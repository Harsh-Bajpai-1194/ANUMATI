import prisma from '../config/db.js';
import { getCached, setCached, deleteCached } from '../config/redis.js';
import { broadcastStatusTransition } from '../services/realtimeService.js';

export const createApplication = async (req, res) => {
  try {
    const { institutionId, applicationType, academicYear } = req.body;
    
    if (req.user.role === 'applicant' && req.user.institutionId !== institutionId) {
      return res.status(403).json({ success: false, message: 'Cannot create application for another institution' });
    }

    // Use Prisma transaction to ensure atomicity
    const application = await prisma.$transaction(async (tx) => {
      const newApp = await tx.application.create({
        data: {
          institutionId,
          applicationType,
          academicYear,
          currentStatus: 'draft'
        }
      });

      await tx.applicationStatusLog.create({
        data: {
          applicationId: newApp.applicationId,
          newStatus: 'draft',
          changedBy: req.user.userId
        }
      });

      return newApp;
    });

    // Real-Time Broadcast: Application created (Draft)
    await broadcastStatusTransition({
      type: 'STATUS_TRANSITION',
      applicationId: application.applicationId,
      status: 'Draft',
      message: 'New application initiated in Draft status.'
    });

    res.status(201).json({ success: true, application });
  } catch (error) {
    if (error.code === 'P2002') {
      return res.status(400).json({ success: false, message: 'Application already exists for this type and academic year' });
    }
    console.error('Create Application Error:', error);
    res.status(500).json({ success: false, message: 'Internal server error' });
  }
};

export const listApplications = async (req, res) => {
  try {
    const { status } = req.query;
    let where = {};

    if (req.user.role === 'applicant') {
      where.institutionId = req.user.institutionId;
    }

    if (status) {
      where.currentStatus = status;
    }

    const applications = await prisma.application.findMany({
      where,
      include: {
        institution: { select: { name: true } }
      },
      orderBy: { createdAt: 'desc' }
    });

    res.status(200).json({ success: true, applications });
  } catch (error) {
    console.error('List Applications Error:', error);
    res.status(500).json({ success: false, message: 'Internal server error' });
  }
};

/**
 * Get Application by ID with Redis Caching (Issue #118)
 */
export const getApplicationById = async (req, res) => {
  try {
    const { id } = req.params;
    const cacheKey = `cache:app:${id}`;

    // 1. Try to fetch from Redis Cache
    const cachedApplication = await getCached(cacheKey);
    if (cachedApplication) {
      if (req.user.role === 'applicant' && cachedApplication.institutionId !== req.user.institutionId) {
        return res.status(403).json({ success: false, message: 'Access denied' });
      }
      res.setHeader('X-Cache', 'HIT');
      return res.status(200).json({ success: true, application: cachedApplication });
    }

    // 2. Cache miss: Query SQL database via Prisma
    const application = await prisma.application.findUnique({
      where: { applicationId: id },
      include: {
        institution: true,
        statusLogs: {
          orderBy: { changedAt: 'desc' },
          include: { user: { select: { fullName: true, role: true } } }
        }
      }
    });

    if (!application) {
      return res.status(404).json({ success: false, message: 'Application not found' });
    }

    if (req.user.role === 'applicant' && application.institutionId !== req.user.institutionId) {
      return res.status(403).json({ success: false, message: 'Access denied' });
    }

    // 3. Store result in Redis with 60-second TTL
    await setCached(cacheKey, application, 60);

    res.setHeader('X-Cache', 'MISS');
    res.status(200).json({ success: true, application });
  } catch (error) {
    console.error('Get Application Error:', error);
    res.status(500).json({ success: false, message: 'Internal server error' });
  }
};

export const submitApplication = async (req, res) => {
  try {
    const { id } = req.params;

    const application = await prisma.application.findUnique({ where: { applicationId: id } });
    if (!application) {
      return res.status(404).json({ success: false, message: 'Application not found' });
    }

    if (req.user.role === 'applicant' && application.institutionId !== req.user.institutionId) {
      return res.status(403).json({ success: false, message: 'Access denied' });
    }

    if (application.currentStatus !== 'draft' && application.currentStatus !== 'returned_for_correction') {
      return res.status(400).json({ success: false, message: 'Application must be in draft or returned_for_correction state to submit' });
    }

    // Use Prisma transaction to ensure atomicity
    const updatedApp = await prisma.$transaction(async (tx) => {
      const app = await tx.application.update({
        where: { applicationId: id },
        data: {
          currentStatus: 'submitted',
          submittedBy: req.user.userId
        }
      });

      await tx.applicationStatusLog.create({
        data: {
          applicationId: id,
          oldStatus: application.currentStatus,
          newStatus: 'submitted',
          changedBy: req.user.userId
        }
      });

      return app;
    });

    // Invalidate Redis Cache on mutation
    await deleteCached(`cache:app:${id}`);

    // Real-Time Broadcast: Application Submitted
    await broadcastStatusTransition({
      type: 'STATUS_TRANSITION',
      applicationId: id,
      status: 'Submitted',
      message: 'Application submitted for institutional verification.'
    });

    res.status(200).json({ success: true, application: updatedApp });
  } catch (error) {
    console.error('Submit Application Error:', error);
    res.status(500).json({ success: false, message: 'Internal server error' });
  }
};

export const decisionApplication = async (req, res) => {
  try {
    const { id } = req.params;
    const { decision } = req.body; 

    if (!['approved', 'rejected', 'returned_for_correction'].includes(decision)) {
      return res.status(400).json({ success: false, message: 'Invalid decision status' });
    }

    const application = await prisma.application.findUnique({ where: { applicationId: id } });
    if (!application) {
      return res.status(404).json({ success: false, message: 'Application not found' });
    }

    if (application.currentStatus !== 'submitted') {
      return res.status(400).json({ success: false, message: 'Only submitted applications can receive a decision' });
    }

    // Use Prisma transaction to ensure atomicity
    const updatedApp = await prisma.$transaction(async (tx) => {
      const app = await tx.application.update({
        where: { applicationId: id },
        data: {
          currentStatus: decision
        }
      });

      await tx.applicationStatusLog.create({
        data: {
          applicationId: id,
          oldStatus: application.currentStatus,
          newStatus: decision,
          changedBy: req.user.userId
        }
      });

      return app;
    });

    // Invalidate Redis Cache on mutation
    await deleteCached(`cache:app:${id}`);

    // Map internal decision enum to user-facing status label
    const statusLabel = decision === 'approved' ? 'Approved' : decision === 'rejected' ? 'Rejected' : 'Returned for Correction';

    // Real-Time Broadcast: Application Decision
    await broadcastStatusTransition({
      type: 'STATUS_TRANSITION',
      applicationId: id,
      status: statusLabel,
      decision,
      message: `Application decision updated to ${statusLabel}.`
    });

    res.status(200).json({ success: true, application: updatedApp });
  } catch (error) {
    console.error('Decision Application Error:', error);
    res.status(500).json({ success: false, message: 'Internal server error' });
  }
};
