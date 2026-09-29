import path from 'path';
import mongoose from 'mongoose';
import {
  parseAndStoreAiReport,
  dispatchAiEvaluation,
  getAiEvaluationByApplicationId,
  getAiEvaluationById
} from '../services/aiEvaluationService.js';

const uploadDir = path.resolve('uploads');

export const evaluationHealthCheck = (req, res) => {
  res.json({ status: 'ok', service: 'AI Evaluation Service' });
};

// POST /api/evaluations  { applicationId, report }
export const saveEvaluationReport = async (req, res) => {
  try {
    const { applicationId, report } = req.body ?? {};
    const saved = await parseAndStoreAiReport(applicationId, report);
    return res.status(201).json({ success: true, data: saved });
  } catch (error) {
    // The service throws plain Errors for validation problems (and for DB errors);
    // treat as 400 for now. Split into typed errors when auth/validation lands.
    return res.status(400).json({ success: false, message: error.message });
  }
};

// POST /api/evaluations/evaluate  { applicationId, storedName }
// Only a bare filename is accepted; it is resolved inside uploads/ (no client-supplied paths).
export const triggerEvaluation = async (req, res) => {
  const { applicationId, storedName } = req.body ?? {};
  if (typeof applicationId !== 'string' || typeof storedName !== 'string') {
    return res.status(400).json({
      success: false,
      message: 'applicationId and storedName are required strings.'
    });
  }

  const filePath = path.join(uploadDir, path.basename(storedName));
  try {
    const saved = await dispatchAiEvaluation(applicationId, filePath);
    return res.status(201).json({ success: true, data: saved });
  } catch (error) {
    console.error('Evaluation dispatch failed:', error);
    const status = /timed out/i.test(error.message) ? 504 : 502;
    return res.status(status).json({ success: false, message: 'Evaluation failed.' });
  }
};

// GET /api/evaluations/application/:applicationId
export const getEvaluationsByApplication = async (req, res) => {
  try {
    const records = await getAiEvaluationByApplicationId(req.params.applicationId);
    return res.json({ success: true, count: records.length, data: records });
  } catch (error) {
    console.error('Fetch evaluations failed:', error);
    return res.status(500).json({ success: false, message: 'Could not load evaluations.' });
  }
};

// GET /api/evaluations/:id
export const getEvaluationRecordById = async (req, res) => {
  const { id } = req.params;
  if (!mongoose.isValidObjectId(id)) {
    return res.status(400).json({ success: false, message: 'Invalid evaluation id.' });
  }
  try {
    const record = await getAiEvaluationById(id);
    if (!record) {
      return res.status(404).json({ success: false, message: 'Evaluation not found.' });
    }
    return res.json({ success: true, data: record });
  } catch (error) {
    console.error('Fetch evaluation failed:', error);
    return res.status(500).json({ success: false, message: 'Could not load evaluation.' });
  }
};
