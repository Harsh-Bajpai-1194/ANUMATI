const API_BASE_URL = 'http://localhost:5000/api';

/**
 * Upload a PDF file to the backend Express server
 * @param {File} file 
 * @returns {Promise<Object>}
 */
export const uploadPdfDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.message || 'Failed to upload document.');
  }

  return result;
};