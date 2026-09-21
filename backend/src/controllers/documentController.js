/* Handle single PDF upload and return metadata */
export const uploadDocument = async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        success: false,
        message: 'No file uploaded or file rejected. Only PDF files up to 15MB are allowed.'
      });
    }

    const { filename, originalname, size, path: filePath, mimetype } = req.file;

    // Document response object
    const documentData = {
      documentId: filename,
      originalName: originalname,
      storedName: filename,
      filePath: filePath,
      sizeBytes: size,
      sizeMb: (size / (1024 * 1024)).toFixed(2),
      mimetype: mimetype,
      uploadedAt: new Date().toISOString(),
      status: 'uploaded'
    };

    return res.status(201).json({
      success: true,
      message: 'Document uploaded successfully.',
      data: documentData
    });
  } catch (error) {
    console.error('Error handling document upload:', error);
    return res.status(500).json({
      success: false,
      message: 'Internal server error while uploading document.'
    });
  }
};

/* Health check for the document service */
export const documentHealthCheck = (req, res) => {
  res.json({ status: 'ok', service: 'Document Service' });
};