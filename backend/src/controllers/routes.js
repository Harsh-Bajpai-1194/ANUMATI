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

const router = Router();

// ==========================================
// Document Service Routes
// ==========================================
router.get('/documents/health', documentHealthCheck);

router.post('/documents/upload', (req, res, next) => {
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

// Ingest raw JSON evaluation report into MongoDB
router.post('/evaluations', saveEvaluationReport);

// Trigger evaluation on ML service and save result
router.post('/evaluations/evaluate', triggerEvaluation);

// Retrieve all evaluation reports for an application (for Evaluator Dashboard)
router.get('/evaluations/application/:applicationId', getEvaluationsByApplication);

// Retrieve a single evaluation report by MongoDB ObjectId
router.get('/evaluations/:id', getEvaluationRecordById);

export default router;