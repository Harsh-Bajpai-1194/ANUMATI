import fs from 'fs';
import path from 'path';
import AiEvaluation from '../models/AiEvaluation.js';
import { ML_INTERNAL_TOKEN } from '../config/auth.js';

const VALID_SEVERITIES = new Set(['low', 'medium', 'high', 'critical']);

/**
 * Strict JSON Contract Validator (Issue #117)
 * Validates the verification report schema returned by FastAPI before storing in MongoDB.
 */
export const validateAiReportContract = (rawReport) => {
  if (!rawReport || typeof rawReport !== 'object' || Array.isArray(rawReport)) {
    throw new Error('Contract Violation: Verification report must be a non-null JSON object.');
  }

  if (rawReport.status && !['completed', 'success'].includes(String(rawReport.status).toLowerCase())) {
    throw new Error(`Contract Violation: Incomplete evaluation status "${rawReport.status}".`);
  }

  const hasExtraction = Boolean(rawReport.textExtraction || rawReport.extractedTextMetadata);
  const hasAnomaly = Boolean(rawReport.anomalyDetection);

  if (!hasExtraction && !hasAnomaly) {
    throw new Error('Contract Violation: Missing required text extraction or anomaly detection fields.');
  }

  if (rawReport.anomalyDetection) {
    if (typeof rawReport.anomalyDetection !== 'object' || Array.isArray(rawReport.anomalyDetection)) {
      throw new Error('Contract Violation: "anomalyDetection" must be an object.');
    }
    if (rawReport.anomalyDetection.flags && !Array.isArray(rawReport.anomalyDetection.flags)) {
      throw new Error('Contract Violation: "anomalyDetection.flags" must be an array.');
    }
  }

  if (rawReport.complianceScore !== undefined && typeof rawReport.complianceScore !== 'number') {
    throw new Error('Contract Violation: "complianceScore" must be a numeric value.');
  }

  return true;
};

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

export const resolveIdentifiers = (identifiers) => {
  let applicationId = null;
  let documentId = null;

  if (typeof identifiers === 'string') {
    applicationId = identifiers.trim() || null;
  } else if (identifiers && typeof identifiers === 'object') {
    applicationId = typeof identifiers.applicationId === 'string' && identifiers.applicationId.trim() ? identifiers.applicationId.trim() : null;
    documentId = typeof identifiers.documentId === 'string' && identifiers.documentId.trim() ? identifiers.documentId.trim() : null;
  }

  if (!applicationId && !documentId) {
    throw new Error('A valid applicationId or documentId string is required to store an AI evaluation report.');
  }

  return { applicationId, documentId };
};

export const parseAndStoreAiReport = async (identifiers, rawReport) => {
  const { applicationId, documentId } = resolveIdentifiers(identifiers);

  // Enforce JSON Schema Contract before persisting
  validateAiReportContract(rawReport);

  const ocrConfidenceScore =
    rawReport.textExtraction?.ocrConfidenceScore ??
    rawReport.extractedTextMetadata?.ocrConfidenceScore ??
    null;

  const extractedEntities =
    rawReport.textExtraction?.extractedEntities ??
    rawReport.extractedTextMetadata?.extractedEntities ??
    {};

  const anomalySource = rawReport.anomalyDetection || {};
  const isFlagged = Boolean(anomalySource.flagged);
  const flags = normalizeFlags(anomalySource.flags);
  
  const complianceScore = typeof rawReport.complianceScore === 'number' ? rawReport.complianceScore : 0;

  const evaluationPayload = {
    complianceScore,
    extractedTextMetadata: {
      ocrConfidenceScore,
      extractedEntities
    },
    anomalyDetection: {
      flagged: isFlagged,
      flags
    },
    rawModelResponse: rawReport
  };

  if (applicationId) {
    evaluationPayload.applicationId = applicationId;
  }
  if (documentId) {
    evaluationPayload.documentId = documentId;
  }

  const evaluationDocument = new AiEvaluation(evaluationPayload);
  const savedRecord = await evaluationDocument.save();
  const targetLabel = applicationId ? `application ${applicationId}` : `document ${documentId}`;
  console.log(`[AI Evaluation Service] Report saved for ${targetLabel} (Mongo ID: ${savedRecord._id})`);
  return savedRecord;
};

export const dispatchAiEvaluation = async (identifiers, filePath) => {
  const { applicationId, documentId } = resolveIdentifiers(identifiers);

  const absolutePath = path.resolve(filePath);
  if (!fs.existsSync(absolutePath)) {
    throw new Error(`File not found at path: ${absolutePath}`);
  }

  const mlServiceUrl = process.env.ML_SERVICE_URL || 'http://127.0.0.1:8000';
  const requestTimeoutMs = parseInt(process.env.ML_REQUEST_TIMEOUT_MS, 10) || 60000;
  const fileName = path.basename(absolutePath);
  const targetLabel = applicationId ? `application ${applicationId}` : `document ${documentId || 'unknown'}`;

  console.log(`[ML Dispatcher] Sending ${targetLabel} (${fileName}) to ML Service at ${mlServiceUrl}/evaluate...`);

  const fileBlob = await fs.openAsBlob(absolutePath, { type: 'application/pdf' });
  const formData = new FormData();
  formData.append('file', fileBlob, fileName);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), requestTimeoutMs);

  try {
    // Send dual token headers to enforce internal microservice gatekeeping
    const response = await fetch(`${mlServiceUrl}/evaluate`, {
      method: 'POST',
      headers: {
        'X-Internal-Token': ML_INTERNAL_TOKEN,
        'X-API-Key': ML_INTERNAL_TOKEN
      },
      body: formData,
      signal: controller.signal
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `ML Service responded with HTTP ${response.status}`);
    }

    const evaluationResult = await response.json();
    console.log(`[ML Dispatcher] ML evaluation received for ${targetLabel}. Storing report...`);

    return await parseAndStoreAiReport({ applicationId, documentId }, evaluationResult);
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error(`ML evaluation request timed out after ${requestTimeoutMs}ms`);
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
};

export const getAiEvaluationByApplicationId = async (applicationId) => {
  if (!applicationId) throw new Error('applicationId parameter is required.');
  return await AiEvaluation.find({ applicationId }).sort({ createdAt: -1 }).lean();
};

export const getAiEvaluationByDocumentId = async (documentId) => {
  if (!documentId) throw new Error('documentId parameter is required.');
  return await AiEvaluation.find({ documentId }).sort({ createdAt: -1 }).lean();
};

export const getAiEvaluationById = async (id) => {
  if (!id) throw new Error('Evaluation ID parameter is required.');
  return await AiEvaluation.findById(id).lean();
};
