import { Router } from 'express';
import {
  uploadPdf,
  validatePdfContent,
  loginLimiter,
  uploadLimiter,
  apiGatewayLimiter,
  handleMulterUpload
} from '../src/middleware/middleware.js';
import {
  uploadDocument,
  documentHealthCheck,
  getDocumentStatus,
  listDocuments,
  deleteDocument
} from '../src/controllers/documentController.js';
import {
  saveEvaluationReport,
  triggerEvaluation,
  getEvaluationsByApplication,
  getEvaluationRecordById,
  evaluationHealthCheck
} from '../src/controllers/aiEvaluationController.js';
import { register, login } from '../src/controllers/authController.js';
import { requireAuth, optionalAuth, requireRole } from '../src/middleware/authMiddleware.js';
import {
  createApplication,
  listApplications,
  getApplicationById,
  submitApplication,
  decisionApplication
} from '../src/controllers/applicationController.js';

const router = Router();

// Apply Global Gateway Rate Limiting to all /api traffic
router.use(apiGatewayLimiter);

// Gateway Health Check
router.get('/health', (req, res) => {
  res.status(200).json({
    status: 'UP',
    gateway: 'ANUMATI Centralized API Gateway',
    timestamp: new Date().toISOString()
  });
});

// ==========================================
// Auth & RBAC Routes (with loginLimiter)
// ==========================================
router.post('/auth/register', register);
router.post('/auth/login', loginLimiter, login);

// ==========================================
// Document Service Routes (with uploadLimiter & 15MB enforcement)
// ==========================================
router.get('/documents/health', documentHealthCheck);
router.get('/documents', requireAuth, listDocuments);
router.get('/documents/application/:applicationId', requireAuth, listDocuments);

router.post(
  '/documents/upload',
  uploadLimiter,
  optionalAuth,
  handleMulterUpload(uploadPdf.single('file')),
  validatePdfContent,
  uploadDocument
);

router.get('/documents/:id', optionalAuth, getDocumentStatus);
router.delete('/documents/:id', requireAuth, deleteDocument);

// ==========================================
// AI Evaluation & Report Storage Routes
// ==========================================
router.get('/evaluations/health', evaluationHealthCheck);
router.post('/evaluations', requireAuth, saveEvaluationReport);
router.post('/evaluations/evaluate', requireAuth, triggerEvaluation);
router.get('/evaluations/application/:applicationId', requireAuth, getEvaluationsByApplication);
router.get('/evaluations/:id', requireAuth, getEvaluationRecordById);

// ==========================================
// Application Lifecycle Routes
// ==========================================
router.post('/applications', requireAuth, requireRole(['applicant', 'admin']), createApplication);
router.get('/applications', requireAuth, listApplications);
router.get('/applications/:id', requireAuth, getApplicationById);
router.post('/applications/:id/submit', requireAuth, requireRole(['applicant', 'admin']), submitApplication);
router.post(
  '/applications/:id/decision',
  requireAuth,
  requireRole(['evaluator', 'admin']),
  decisionApplication
);

export default router;