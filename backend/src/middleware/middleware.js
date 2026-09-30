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
 * Safely removes rejected files from disk, logging non-ENOENT errors.
 */
const safeDeleteFile = async (targetPath) => {
  try {
    const resolvedUploadDir = path.resolve(uploadDir);
    const resolvedTarget = path.resolve(targetPath);
    if (resolvedTarget.startsWith(resolvedUploadDir + path.sep)) {
      await fs.promises.unlink(resolvedTarget);
    }
  } catch (err) {
    if (err.code !== 'ENOENT') {
      console.error(`Failed to delete rejected upload at ${targetPath}:`, err);
    }
  }
};

/**
 * Validates uploaded file magic numbers to ensure genuine PDF format (%PDF-).
 * Confines file paths to the upload directory and guarantees file descriptor closure.
 */
export const validatePdfContent = async (req, res, next) => {
  if (!req.file) return next();

  // CodeQL Fix: Ensure path is strictly contained within uploadDir
  const resolvedUploadDir = path.resolve(uploadDir);
  const filePath = path.resolve(req.file.path);
  const isWithinUploadDir =
    filePath === resolvedUploadDir || filePath.startsWith(resolvedUploadDir + path.sep);

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
      await safeDeleteFile(filePath);
      return res.status(400).json({
        success: false,
        message: 'Security validation failed: File content does not match a valid PDF signature.'
      });
    }

    next();
  } catch (error) {
    await safeDeleteFile(filePath);
    return res.status(400).json({
      success: false,
      message: 'Failed to inspect uploaded file.'
    });
  } finally {
    // CodeRabbit Fix: Always close file descriptor even if read fails
    if (fd) {
      await fd.close().catch(() => {});
    }
  }
};
