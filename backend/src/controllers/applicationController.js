import prisma from '../config/db.js';

// POST /api/applications (applicant)
export const createApplication = async (req, res) => {
  try {
    const { institutionId, applicationType, academicYear } = req.body;
    
    // Validate applicant is creating for their own institution, unless they are admin
    if (req.user.role === 'applicant' && req.user.institutionId !== institutionId) {
      return res.status(403).json({ success: false, message: 'Cannot create application for another institution' });
    }

    const application = await prisma.application.create({
      data: {
        institutionId,
        applicationType,
        academicYear,
        currentStatus: 'draft'
      }
    });

    // Create initial status log
    await prisma.applicationStatusLog.create({
      data: {
        applicationId: application.applicationId,
        newStatus: 'draft',
        changedBy: req.user.userId
      }
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

// GET /api/applications (applicant: own institution; evaluator/admin: all, filter by status)
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

// GET /api/applications/:id
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

    // Access control check
    if (req.user.role === 'applicant' && application.institutionId !== req.user.institutionId) {
      return res.status(403).json({ success: false, message: 'Access denied' });
    }

    res.status(200).json({ success: true, application });
  } catch (error) {
    console.error('Get Application Error:', error);
    res.status(500).json({ success: false, message: 'Internal server error' });
  }
};

// POST /api/applications/:id/submit
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

    const updatedApp = await prisma.application.update({
      where: { applicationId: id },
      data: {
        currentStatus: 'submitted',
        submittedBy: req.user.userId
      }
    });

    await prisma.applicationStatusLog.create({
      data: {
        applicationId: id,
        oldStatus: application.currentStatus,
        newStatus: 'submitted',
        changedBy: req.user.userId
      }
    });

    res.status(200).json({ success: true, application: updatedApp });
  } catch (error) {
    console.error('Submit Application Error:', error);
    res.status(500).json({ success: false, message: 'Internal server error' });
  }
};

// POST /api/applications/:id/decision
export const decisionApplication = async (req, res) => {
  try {
    const { id } = req.params;
    const { decision } = req.body; // 'approved', 'rejected', 'returned_for_correction'

    if (!['approved', 'rejected', 'returned_for_correction'].includes(decision)) {
      return res.status(400).json({ success: false, message: 'Invalid decision status' });
    }

    const application = await prisma.application.findUnique({ where: { applicationId: id } });
    if (!application) {
      return res.status(404).json({ success: false, message: 'Application not found' });
    }

    const updatedApp = await prisma.application.update({
      where: { applicationId: id },
      data: {
        currentStatus: decision
      }
    });

    await prisma.applicationStatusLog.create({
      data: {
        applicationId: id,
        oldStatus: application.currentStatus,
        newStatus: decision,
        changedBy: req.user.userId
      }
    });

    res.status(200).json({ success: true, application: updatedApp });
  } catch (error) {
    console.error('Decision Application Error:', error);
    res.status(500).json({ success: false, message: 'Internal server error' });
  }
};