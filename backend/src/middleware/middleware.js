import multer from 'multer';
import path from 'path';
import fs from 'fs';
import crypto from 'crypto';

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
    // Generate a unique prefix: timestamp + random bytes
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

/**
 * Validates uploaded file magic numbers to ensure genuine PDF format (%PDF-).
 * If the file is not a genuine PDF, it is immediately unlinked from disk and a 400 is returned.
 */
export const validatePdfContent = async (req, res, next) => {
  if (!req.file) return next();

  const filePath = req.file.path;
  try {
    const fd = await fs.promises.open(filePath, 'r');
    const buffer = Buffer.alloc(1024);
    const { bytesRead } = await fd.read(buffer, 0, 1024, 0);
    await fd.close();

    const header = buffer.subarray(0, bytesRead).toString('latin1');
    if (!header.includes('%PDF-')) {
      // Remove invalid/malicious non-PDF file from disk
      await fs.promises.unlink(filePath).catch(() => {});
      return res.status(400).json({
        success: false,
        message: 'Security validation failed: File content does not match a valid PDF signature.'
      });
    }

    next();
  } catch (error) {
    if (fs.existsSync(filePath)) {
      await fs.promises.unlink(filePath).catch(() => {});
    }
    return res.status(400).json({
      success: false,
      message: 'Failed to inspect uploaded file.'
    });
  }
};
