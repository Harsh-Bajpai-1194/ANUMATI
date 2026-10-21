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

// POST /api/evaluations  { applicationId, documentId, report }
export const saveEvaluationReport = async (req, res) => {
  try {
    const { applicationId, documentId, report } = req.body ?? {};
    const saved = await parseAndStoreAiReport({ applicationId, documentId }, report);
    return res.status(201).json({ success: true, data: saved });
  } catch (error) {
    return res.status(400).json({ success: false, message: error.message });
  }
};

// POST /api/evaluations/evaluate  { applicationId, documentId, storedName }
// Only a bare filename is accepted; it is resolved inside uploads/ (no client-supplied paths).
export const triggerEvaluation = async (req, res) => {
  const { applicationId, documentId, storedName } = req.body ?? {};
  const trimmedAppId = typeof applicationId === 'string' ? applicationId.trim() : '';
  const trimmedDocId = typeof documentId === 'string' ? documentId.trim() : '';
  const trimmedStoredName = typeof storedName === 'string' ? storedName.trim() : '';

  if ((!trimmedAppId && !trimmedDocId) || !trimmedStoredName) {
    return res.status(400).json({
      success: false,
      message: 'A non-empty applicationId or documentId and storedName are required strings.'
    });
  }

  const filePath = path.join(uploadDir, path.basename(trimmedStoredName));
  try {
    const saved = await dispatchAiEvaluation(
      { applicationId: trimmedAppId || null, documentId: trimmedDocId || null },
      filePath
    );
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
