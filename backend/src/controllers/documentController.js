import Document from '../models/Document.js';
import { enqueueEvaluation } from '../services/evaluationQueue.js';

export const uploadDocument = async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        success: false,
        message: 'No file uploaded or file rejected. Only PDF files up to 15MB are allowed.'
      });
    }

    // Use provided applicationId, or logged-in user, or a fallback default
    const applicationId = req.body.applicationId || req.user?.userId || 'demo-application-id';

    const { filename, originalname, size, path: filePath, mimetype } = req.file;

    const doc = new Document({
      applicationId,
      originalName: originalname,
      storedName: filename,
      filePath: filePath,
      sizeBytes: size,
      mimetype: mimetype,
      status: 'uploaded'
    });

    await doc.save();

    // Trigger background evaluation queue asynchronously
    enqueueEvaluation();

    return res.status(201).json({
      success: true,
      message: 'Document uploaded successfully and queued for AI evaluation.',
      data: doc
    });
  } catch (error) {
    console.error('Error handling document upload:', error);
    return res.status(500).json({
      success: false,
      message: 'Internal server error while uploading document.'
    });
  }
};

// Polling endpoint for the React frontend
export const getDocumentStatus = async (req, res) => {
  try {
    const doc = await Document.findById(req.params.id);
    if (!doc) {
      return res.status(404).json({ success: false, message: 'Document not found.' });
    }
    return res.status(200).json({ success: true, data: doc });
  } catch (error) {
    console.error('Error fetching document status:', error);
    return res.status(500).json({ success: false, message: 'Internal server error.' });
  }
};

export const documentHealthCheck = (req, res) => {
  res.json({ status: 'ok', service: 'Document Service' });
};
