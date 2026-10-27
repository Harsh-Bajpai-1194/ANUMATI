import multer from 'multer';
import path from 'path';
import fs from 'fs';
import crypto from 'crypto';
import rateLimit from 'express-rate-limit';

// ============================================================================
// Gateway Rate Limiters (Issue #117)
// ============================================================================

/**
 * Strict Rate Limiter for Authentication endpoints (/auth/login)
 * Mitigates credential stuffing and brute-force attacks.
 */
export const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 10, // Max 10 attempts per IP per 15 minutes
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    success: false,
    message: 'Too many login attempts from this IP. Please try again after 15 minutes.'
  }
});

/**
 * Upload Throttling Limiter for Document endpoints (/documents/upload)
 * Prevents DoS bottlenecks and abuse through high-volume PDF uploads.
 */
export const uploadLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 20, // Max 20 file uploads per IP per 15 minutes
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    success: false,
    message: 'Upload rate limit exceeded. Please try again after 15 minutes.'
  }
});

/**
 * Global API Gateway Rate Limiter
 */
export const apiGatewayLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 150, // 150 requests per IP per 15 minutes
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    success: false,
    message: 'API rate limit exceeded. Please slow down and try again later.'
  }
});

// Ensure the upload directory exists.
const uploadDir = path.resolve('uploads');
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true });
}

// Storage configuration: save to disk with unique filenames.
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = `${Date.now()}-${crypto.randomBytes(6).toString('hex')}`;
    const cleanFileName = file.originalname.replace(/[^a-zA-Z0-9.-]/g, '_');
    cb(null, `${uniqueSuffix}-${cleanFileName}`);
  }
});

// File filter: check client-supplied MIME type
const fileFilter = (req, file, cb) => {
  if (file.mimetype === 'application/pdf') {
    cb(null, true);
  } else {
    cb(new Error('Invalid file format. Only PDF files are allowed.'), false);
  }
};

// 15MB limit as defined in system requirements
export const uploadPdf = multer({
  storage,
  fileFilter,
  limits: {
    fileSize: 15 * 1024 * 1024 // 15 Megabytes
  }
});

export const handleMulterUpload = (uploadMiddleware) => (req, res, next) => {
  uploadMiddleware(req, res, (err) => {
    if (err) {
      if (err.code === 'LIMIT_FILE_SIZE') {
        return res.status(413).json({
          success: false,
          message: 'Payload too large: PDF file exceeds the 15MB gateway limit.'
        });
      }
      return res.status(400).json({
        success: false,
        message: err.message || 'File upload error.'
      });
    }
    next();
  });
};

/**
 * Safely removes rejected files from disk, logging non-ENOENT errors.
 * Avoids template literal in console.error to prevent CodeQL format string warnings.
 */
const safeDeleteFile = async (fileNameOrPath) => {
  try {
    const resolvedUploadDir = path.resolve(uploadDir);
    const safeName = path.basename(fileNameOrPath);
    const safeTarget = path.resolve(resolvedUploadDir, safeName);
    if (safeTarget.startsWith(resolvedUploadDir + path.sep)) {
      await fs.promises.unlink(safeTarget);
    }
  } catch (err) {
    if (err.code !== 'ENOENT') {
      console.error('Failed to delete rejected upload:', err);
    }
  }
};

/**
 * Validates uploaded file magic numbers to ensure genuine PDF format (%PDF-).
 * Confines file paths to the upload directory using path.basename() sanitization.
 */
export const validatePdfContent = async (req, res, next) => {
  if (!req.file) return next();

  // CodeQL Fix: Strip directory traversal using path.basename and verify containment
  const resolvedUploadDir = path.resolve(uploadDir);
  const safeFileName = path.basename(req.file.filename || req.file.path);
  const filePath = path.resolve(resolvedUploadDir, safeFileName);
  const isWithinUploadDir = filePath.startsWith(resolvedUploadDir + path.sep);

  if (!isWithinUploadDir) {
    return res.status(400).json({
      success: false,
      message: 'Security validation failed: Invalid upload path.'
    });
  }

  let fd;
  try {
    fd = await fs.promises.open(filePath, 'r');
    const buffer = Buffer.alloc(1024);
    const { bytesRead } = await fd.read(buffer, 0, 1024, 0);

    const header = buffer.subarray(0, bytesRead).toString('latin1');
    if (!header.includes('%PDF-')) {
      await safeDeleteFile(safeFileName);
      return res.status(400).json({
        success: false,
        message: 'Security validation failed: File content does not match a valid PDF signature.'
      });
    }

    next();
  } catch (error) {
    await safeDeleteFile(safeFileName);
    return res.status(400).json({
      success: false,
      message: 'Failed to inspect uploaded file.'
    });
  } finally {
    if (fd) {
      await fd.close().catch(() => {});
    }
  }
};
