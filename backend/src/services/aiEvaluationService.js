import path from 'path';
import AiEvaluation from '../models/AiEvaluation.js';

const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://127.0.0.1:8000';
const ML_REQUEST_TIMEOUT_MS = parseInt(process.env.ML_REQUEST_TIMEOUT_MS, 10) || 60000;

const VALID_SEVERITIES = new Set(['low', 'medium', 'high', 'critical']);

/**
 * Normalizes rule violation / anomaly flags to match AiEvaluation schema
 * @param {Array} rawFlags
 * @returns {Array} normalized flags
 */
const normalizeFlags = (rawFlags = []) => {
  if (!Array.isArray(rawFlags)) return [];

  return rawFlags.map((flag) => {
    let severity = (flag.severity || 'medium').toLowerCase();
    if (!VALID_SEVERITIES.has(severity)) {
      severity = severity === 'warning' ? 'medium' : severity === 'error' ? 'high' : 'medium';
    }

    return {
      ruleCode: flag.ruleCode || flag.rule_code || flag.code || 'UNKNOWN_RULE',
      description: flag.description || flag.message || 'No description provided',
      severity
    };
  });
};

/**
 * Parses raw AI JSON report data and persists it to the MongoDB AiEvaluation collection.
 * 
 * @param {string} applicationId - PostgreSQL application ID or document reference
 * @param {Object} rawReport - Full JSON verification report from ML service
 * @returns {Promise<Object>} Saved Mongoose AiEvaluation document
 */
export const parseAndStoreAiReport = async (applicationId, rawReport) => {
  if (!applicationId || typeof applicationId !== 'string') {
    throw new Error('A valid applicationId string is required to store an AI evaluation report.');
  }

  if (!rawReport || typeof rawReport !== 'object' || Array.isArray(rawReport)) {
    throw new Error('A valid JSON report object is required.');
  }

  // Reject incomplete or failed evaluation reports
  if (rawReport.status && rawReport.status !== 'completed' && rawReport.status !== 'success') {
    throw new Error(`Cannot store evaluation with incomplete status: "${rawReport.status}".`);
  }

  const hasExtraction = Boolean(rawReport.textExtraction || rawReport.extractedTextMetadata);
  const hasAnomaly = Boolean(rawReport.anomalyDetection);

  if (!hasExtraction && !hasAnomaly) {
    throw new Error('Invalid evaluation report: Missing required text extraction and anomaly detection fields.');
  }

  // Extract text metadata (supports both ML service schema and legacy schema)
  const ocrConfidenceScore =
    rawReport.textExtraction?.extractionQualityScore ??
    rawReport.extractedTextMetadata?.ocrConfidenceScore ??
    0;

  const extractedEntities =
    rawReport.textExtraction?.extractedEntities ??
    rawReport.extractedTextMetadata?.extractedEntities ??
    {};

  // Extract anomaly flags & detection metadata
  const anomalySource = rawReport.anomalyDetection || {};
  const isFlagged = Boolean(anomalySource.flagged);
  const confidence = typeof anomalySource.confidence === 'number' ? anomalySource.confidence : 0;
  const flags = normalizeFlags(anomalySource.flags);

  // Build and save Mongoose document
  const evaluationDocument = new AiEvaluation({
    applicationId: applicationId.trim(),
    extractedTextMetadata: {
      ocrConfidenceScore,
      extractedEntities
    },
    anomalyDetection: {
      flagged: isFlagged,
      confidence,
      flags
    },
    rawModelResponse: rawReport
  });

  const savedRecord = await evaluationDocument.save();
  console.log(`[AI Evaluation Service] Report saved for application ${applicationId} (Mongo ID: ${savedRecord._id})`);
  return savedRecord;
};

/**
 * Dispatches an uploaded document to FastAPI ML service and saves result in MongoDB
 * 
 * @param {string} applicationId - Application or Document identifier
 * @param {string} filePath - Path to the PDF document
 * @returns {Promise<Object>} Saved AiEvaluation document
 */
export const dispatchAiEvaluation = async (applicationId, filePath) => {
  const absolutePath = path.resolve(filePath);

  console.log(`[ML Dispatcher] Sending ${applicationId} to ML Service at ${ML_SERVICE_URL}/evaluate...`);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), ML_REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${ML_SERVICE_URL}/evaluate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        filePath: absolutePath,
        documentId: applicationId
      }),
      signal: controller.signal
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `ML Service responded with HTTP ${response.status}`);
    }

    const evaluationResult = await response.json();
    console.log(`[ML Dispatcher] ML evaluation received for ${applicationId}. Storing report...`);

    return await parseAndStoreAiReport(applicationId, evaluationResult);
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error(`ML evaluation request timed out after ${ML_REQUEST_TIMEOUT_MS}ms`);
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
};

/**
 * Retrieves AI evaluations for a specific application ID (newest first)
 * @param {string} applicationId 
 * @returns {Promise<Array>} Array of AiEvaluation documents
 */
export const getAiEvaluationByApplicationId = async (applicationId) => {
  if (!applicationId) throw new Error('applicationId parameter is required.');
  return await AiEvaluation.find({ applicationId }).sort({ createdAt: -1 }).lean();
};

/**
 * Retrieves a single AI evaluation report by its MongoDB ObjectId
 * @param {string} id 
 * @returns {Promise<Object|null>} AiEvaluation document or null
 */
export const getAiEvaluationById = async (id) => {
  if (!id) throw new Error('Evaluation ID parameter is required.');
  return await AiEvaluation.findById(id).lean();
};