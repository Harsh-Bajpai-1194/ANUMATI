import { Router } from 'express';
import { uploadPdf } from '../middleware/middleware.js';
import { uploadDocument, documentHealthCheck } from './documentController.js';

const router = Router();

// Health check endpoint for the document service.
router.get('/documents/health', documentHealthCheck);

// Created a Single PDF upload route.
router.post('/documents/upload', (req, res, next) => {
  uploadPdf.single('file')(req, res, (err) => {
    if (err) {
      // Handle Multer errors (file size, file type, etc.)
      return res.status(400).json({
        success: false,
        message: err.message || 'File upload error.'
      });
    }
    next();
  });
}, uploadDocument);

export default router;