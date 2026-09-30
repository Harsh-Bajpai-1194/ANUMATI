import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import prisma from '../config/db.js';
import { enqueueEvaluation } from '../services/evaluationQueue.js';
import AiEvaluation from '../models/AiEvaluation.js';

export const uploadDocument = async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        success: false,
        message: 'No file uploaded or file rejected. Only PDF files up to 15MB are allowed.'
      });
    }

    const { filename, originalname, size, path: filePath } = req.file;

    // Validate that the uploaded file path resolves under the expected uploads directory (CodeQL Fix)
    const uploadRoot = path.resolve('uploads');
    const safeFileName = path.basename(filename || filePath);
    const resolvedFilePath = path.resolve(uploadRoot, safeFileName);
    if (
      !resolvedFilePath.startsWith(uploadRoot + path.sep) ||
      !fs.existsSync(resolvedFilePath)
    ) {
      return res.status(400).json({
        success: false,
        message: 'Invalid uploaded file path.'
      });
    }

    // Compute sha256 checksum of physical file (Issue #35)
    const fileBuffer = fs.readFileSync(resolvedFilePath);
    const sha256 = crypto.createHash('sha256').update(fileBuffer).digest('hex');

    // Validate UUID format if an applicationId is provided
    let validApplicationId = null;
    if (req.body.applicationId) {
      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
      if (uuidRegex.test(req.body.applicationId)) {
        const existingApp = await prisma.application.findUnique({
          where: { applicationId: req.body.applicationId }
        });
        if (existingApp) {
          validApplicationId = req.body.applicationId;
        }
      }
    }

    // Persist document metadata in PostgreSQL via Prisma (Issue #35)
    const doc = await prisma.document.create({
      data: {
        applicationId: validApplicationId,
        originalName: originalname,
        storageKey: safeFileName,
        sha256: sha256,
        sizeBytes: size,
        status: 'uploaded',
        uploadedBy: req.user?.userId || null
      }
    });

    // Trigger background evaluation queue asynchronously (Issue #85)
    enqueueEvaluation();

    // Security (Issue #35, Issue #81): Return UUID and metadata, NEVER the filesystem path!
    return res.status(201).json({
      success: true,
      message: 'Document uploaded successfully and queued for AI evaluation.',
      data: {
        documentId: doc.documentId,
        applicationId: doc.applicationId,
        originalName: doc.originalName,
        sizeBytes: doc.sizeBytes,
        status: doc.status,
        createdAt: doc.createdAt
      }
    });
  } catch (error) {
    console.error('Error handling document upload:', error);
    return res.status(500).json({
      success: false,
      message: 'Internal server error while uploading document.'
    });
  }
};

// Polling endpoint for document status (Issue #35, #85)
export const getDocumentStatus = async (req, res) => {
  try {
    const { id } = req.params;

    const doc = await prisma.document.findUnique({
      where: { documentId: id },
      select: {
        documentId: true,
        applicationId: true,
        originalName: true,
        sizeBytes: true,
        status: true,
        createdAt: true,
        mongoAiEvaluationRef: true
      }
    });

    if (!doc) {
      return res.status(404).json({ success: false, message: 'Document not found.' });
    }

    return res.status(200).json({ success: true, data: doc });
  } catch (error) {
    console.error('Error fetching document status:', error);
    return res.status(500).json({ success: false, message: 'Internal server error.' });
  }
};

// List documents for an application or user (Issue #35)
export const listDocuments = async (req, res) => {
  try {
    const applicationId = req.params.applicationId || req.query.applicationId;
    const where = {};

    if (applicationId) {
      where.applicationId = applicationId;
    } else if (req.user?.role === 'applicant' && req.user?.userId) {
      where.uploadedBy = req.user.userId;
    }

    const documents = await prisma.document.findMany({
      where,
      select: {
        documentId: true,
        applicationId: true,
        originalName: true,
        sizeBytes: true,
        status: true,
        createdAt: true,
        mongoAiEvaluationRef: true
      },
      orderBy: { createdAt: 'desc' }
    });

    return res.status(200).json({ success: true, data: documents });
  } catch (error) {
    console.error('Error listing documents:', error);
    return res.status(500).json({ success: false, message: 'Internal server error while listing documents.' });
  }
};

// Delete document from PostgreSQL and unlink from disk (Issue #35)
export const deleteDocument = async (req, res) => {
  try {
    const { id } = req.params;

    const doc = await prisma.document.findUnique({
      where: { documentId: id }
    });

    if (!doc) {
      return res.status(404).json({ success: false, message: 'Document not found.' });
    }

    // Role-based authorization: applicant can only delete own documents
    if (req.user && req.user.role === 'applicant' && doc.uploadedBy && doc.uploadedBy !== req.user.userId) {
      return res.status(403).json({ success: false, message: 'Forbidden: You can only delete your own documents.' });
    }

    // Delete record from PostgreSQL
    await prisma.document.delete({
      where: { documentId: id }
    });

    // Safely remove physical file from uploads directory (CodeQL Path Sanitization)
    if (doc.storageKey) {
      const uploadRoot = path.resolve('uploads');
      const safeFileName = path.basename(doc.storageKey);
      const targetPath = path.resolve(uploadRoot, safeFileName);
      if (targetPath.startsWith(uploadRoot + path.sep) && fs.existsSync(targetPath)) {
        try {
          fs.unlinkSync(targetPath);
        } catch (unlinkErr) {
          console.error('Failed to unlink document file:', unlinkErr);
        }
      }
    }

    // Clean up MongoDB AI evaluation report if present
    if (doc.mongoAiEvaluationRef) {
      await AiEvaluation.deleteOne({ _id: doc.mongoAiEvaluationRef }).catch(() => {});
    }

    return res.status(200).json({
      success: true,
      message: 'Document deleted successfully.'
    });
  } catch (error) {
    console.error('Error deleting document:', error);
    return res.status(500).json({ success: false, message: 'Internal server error while deleting document.' });
  }
};

export const documentHealthCheck = (req, res) => {
  res.json({ status: 'ok', service: 'Document Service' });
};
