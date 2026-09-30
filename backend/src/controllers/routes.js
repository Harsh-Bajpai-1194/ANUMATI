import { Router } from 'express';
import rateLimit from 'express-rate-limit';
import { uploadPdf, validatePdfContent } from '../middleware/middleware.js';
import {
  uploadDocument,
  documentHealthCheck,
  getDocumentStatus,
  listDocuments,
  deleteDocument
} from './documentController.js';
import {
  saveEvaluationReport,
  triggerEvaluation,
  getEvaluationsByApplication,
  getEvaluationRecordById,
  evaluationHealthCheck
} from './aiEvaluationController.js';

import { register, login } from './authController.js';
import { requireAuth, optionalAuth, requireRole } from '../middleware/authMiddleware.js';
import {
  createApplication,
  listApplications,
  getApplicationById,
  submitApplication,
  decisionApplication
} from './applicationController.js';

const router = Router();

const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, 
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
});
router.use(apiLimiter);

// ==========================================
// Auth & RBAC Routes (Issue #31)
// ==========================================
router.post('/auth/register', register);
router.post('/auth/login', login);

// ==========================================
// Document Service Routes (Issues #25, #35, #81)
// ==========================================
router.get('/documents/health', documentHealthCheck);

// List documents from API
router.get('/documents', requireAuth, listDocuments);
router.get('/documents/application/:applicationId', requireAuth, listDocuments);

// Upload route with optionalAuth, Multer, and content-based %PDF- validation
router.post('/documents/upload', optionalAuth, (req, res, next) => {
  uploadPdf.single('file')(req, res, (err) => {
    if (err) {
      return res.status(400).json({
        success: false,
        message: err.message || 'File upload error.'
      });
    }
    next();
  });
}, validatePdfContent, uploadDocument);

// Get document polling status (Issue #85)
router.get('/documents/:id', optionalAuth, getDocumentStatus);

// Delete document and physical file (Issue #35)
router.delete('/documents/:id', requireAuth, deleteDocument);

// ==========================================
// AI Evaluation & Report Storage Routes (Issue #53)
// ==========================================
router.get('/evaluations/health', evaluationHealthCheck);
router.post('/evaluations', requireAuth, saveEvaluationReport);
router.post('/evaluations/evaluate', requireAuth, triggerEvaluation);
router.get('/evaluations/application/:applicationId', requireAuth, getEvaluationsByApplication);
router.get('/evaluations/:id', requireAuth, getEvaluationRecordById);

// ==========================================
// Application Lifecycle Routes (Issue #87)
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
