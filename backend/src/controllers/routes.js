import { Router } from 'express';
import { uploadPdf } from '../middleware/middleware.js';
import { uploadDocument, documentHealthCheck } from './documentController.js';
import {
  saveEvaluationReport,
  triggerEvaluation,
  getEvaluationsByApplication,
  getEvaluationRecordById,
  evaluationHealthCheck
} from './aiEvaluationController.js';

import { register, login } from './authController.js';
import { requireAuth, requireRole } from '../middleware/authMiddleware.js';
import {
  createApplication,
  listApplications,
  getApplicationById,
  submitApplication,
  decisionApplication
} from './applicationController.js';

const router = Router();

// ==========================================
// Auth & RBAC Routes (Issue #31)
// ==========================================
router.post('/auth/register', register);
router.post('/auth/login', login);

// ==========================================
// Document Service Routes
// ==========================================
router.get('/documents/health', documentHealthCheck);

// Protected upload route
router.post('/documents/upload', requireAuth, (req, res, next) => {
  uploadPdf.single('file')(req, res, (err) => {
    if (err) {
      return res.status(400).json({
        success: false,
        message: err.message || 'File upload error.'
      });
    }
    next();
  });
}, uploadDocument);

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
router.post('/applications', requireAuth, createApplication);
router.get('/applications', requireAuth, listApplications);
router.get('/applications/:id', requireAuth, getApplicationById);

// Applicant Submitting
router.post('/applications/:id/submit', requireAuth, requireRole(['applicant', 'admin']), submitApplication);

// Evaluator/Admin Decisions
router.post(
  '/applications/:id/decision', 
  requireAuth, 
  requireRole(['evaluator', 'admin']), 
  decisionApplication
);

export default router;