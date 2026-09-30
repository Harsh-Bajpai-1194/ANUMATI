import prisma from '../config/db.js';

export const createApplication = async (req, res) => {
  try {
    const { institutionId, applicationType, academicYear } = req.body;
    
    if (req.user.role === 'applicant' && req.user.institutionId !== institutionId) {
      return res.status(403).json({ success: false, message: 'Cannot create application for another institution' });
    }

    // CodeRabbit Fix: Use Prisma transaction to ensure atomicity
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

export const getApplicationById = async (req, res) => {
  try {
    const { id } = req.params;

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

    // CodeRabbit Fix: Use Prisma transaction to ensure atomicity
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

    // CodeRabbit Fix: Enforce allowed status transition
    if (application.currentStatus !== 'submitted') {
      return res.status(400).json({ success: false, message: 'Only submitted applications can receive a decision' });
    }

    // CodeRabbit Fix: Use Prisma transaction to ensure atomicity
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

    res.status(200).json({ success: true, application: updatedApp });
  } catch (error) {
    console.error('Decision Application Error:', error);
    res.status(500).json({ success: false, message: 'Internal server error' });
  }
};