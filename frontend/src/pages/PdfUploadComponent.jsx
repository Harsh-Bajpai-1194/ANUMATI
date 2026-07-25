import React, { useState, useRef } from 'react';

const PdfUploadComponent = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [isHovered, setIsHovered] = useState(false);
  
  const fileInputRef = useRef(null);

  const MAX_FILE_SIZE = 15 * 1024 * 1024; 

  const handleFileChange = (event) => {
    setErrorMessage('');
    setSuccessMessage('');
    setSelectedFile(null);

    const file = event.target.files[0];

    if (!file) return;

    if (file.type !== 'application/pdf') {
      setErrorMessage('Invalid file format. Please upload a PDF file.');
      resetInput();
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setErrorMessage('Size exceed. Maximum allowed file size is 15MB.');
      resetInput();
      return;
    }
    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {      
      console.log('Uploading:', selectedFile.name);
      
      setUploadedFiles((prevFiles) => [...prevFiles, selectedFile]);
      
      setSuccessMessage(`${selectedFile.name} uploaded successfully!`);
      
      setTimeout(() => setSuccessMessage(''), 3000);
      
      setSelectedFile(null);
      resetInput();
    } catch (error) {
      setErrorMessage('Failed to upload file. Please try again.');
    }
  };

  const handleDelete = (indexToRemove) => {
    setUploadedFiles((prevFiles) => 
      prevFiles.filter((_, index) => index !== indexToRemove)
    );
  };

  const resetInput = () => {
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.header}>Upload PDF Document</h2>
      
      <div 
        style={{
          ...styles.uploadBox,
          borderColor: isHovered ? '#007bff' : '#ccc',
          backgroundColor: isHovered ? '#f1f8ff' : '#fafafa'
        }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <p style={styles.uploadPrompt}>Click here to select a PDF</p>
        <p style={styles.uploadSubPrompt}>Max file size: 15MB</p>
        <input
          type="file"
          accept="application/pdf"
          onChange={handleFileChange}
          ref={fileInputRef}
          style={styles.input}
        />
      </div>

      {errorMessage && <p style={styles.errorText}>{errorMessage}</p>}
      {successMessage && <p style={styles.successText}>{successMessage}</p>}

      {selectedFile && (
        <div style={styles.fileDetails}>
          <p style={{ margin: '0 0 5px 0' }}><strong>Ready to upload:</strong> {selectedFile.name}</p>
          <p style={{ margin: '0' }}><strong>Size:</strong> {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</p>
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={!selectedFile}
        style={{
          ...styles.button,
          backgroundColor: selectedFile ? '#007bff' : '#cccccc',
          cursor: selectedFile ? 'pointer' : 'not-allowed',
        }}
      >
        Upload File
      </button>

      {uploadedFiles.length > 0 && (
        <div style={styles.uploadedSection}>
          <h3 style={styles.uploadedHeader}>Uploaded Files</h3>
          <ul style={styles.fileList}>
            {uploadedFiles.map((file, index) => (
              <li key={index} style={styles.fileListItem}>
                <div style={styles.fileInfo}>
                  <span style={styles.fileName}>{file.name}</span>
                  <span style={styles.fileSize}>{(file.size / (1024 * 1024)).toFixed(2)} MB</span>
                </div>
                <button 
                  onClick={() => handleDelete(index)}
                  style={styles.deleteButton}
                  title="Delete file"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
          <a href="/dashboard.html" style={{ textDecoration: 'none' }}>
            <button
              style={{
                ...styles.button,
                marginTop: '20px',
                backgroundColor: '#28a745',
                cursor: 'pointer',
              }}
            >
              Next
            </button>
          </a>
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    maxWidth: '450px',
    margin: '40px auto',
    padding: '30px',
    border: '1px solid #eaeaea',
    borderRadius: '12px',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    boxShadow: '0 8px 24px rgba(0,0,0,0.08)',
    backgroundColor: 'white'
  },
  header: {
    marginTop: 0,
    marginBottom: '20px',
    color: '#333',
    fontSize: '1.5rem',
    textAlign: 'center'
  },
  uploadBox: {
    position: 'relative',
    marginBottom: '20px',
    padding: '40px 20px',
    border: '2px dashed',
    borderRadius: '8px',
    textAlign: 'center',
    transition: 'all 0.2s ease',
    cursor: 'pointer',
    overflow: 'hidden'
  },
  uploadPrompt: {
    margin: 0,
    fontSize: '1.1rem',
    color: '#007bff',
    fontWeight: '600'
  },
  uploadSubPrompt: {
    margin: '8px 0 0 0',
    fontSize: '0.85rem',
    color: '#666'
  },
  input: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    opacity: 0,
    cursor: 'pointer'
  },
  errorText: {
    color: '#dc3545',
    fontWeight: '500',
    marginTop: '0',
    marginBottom: '15px',
    textAlign: 'center'
  },
  successText: {
    color: '#28a745',
    fontWeight: '500',
    marginTop: '0',
    marginBottom: '15px',
    textAlign: 'center',
    padding: '10px',
    backgroundColor: '#d4edda',
    borderRadius: '6px'
  },
  fileDetails: {
    backgroundColor: '#f8f9fa',
    border: '1px solid #e2e8f0',
    padding: '12px',
    borderRadius: '6px',
    marginBottom: '15px',
    fontSize: '0.9rem',
    color: '#4a5568'
  },
  button: {
    width: '100%',
    padding: '12px',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '1.05rem',
    fontWeight: 'bold',
    transition: 'background-color 0.2s'
  },
  uploadedSection: {
    marginTop: '30px',
    borderTop: '1px solid #eaeaea',
    paddingTop: '20px'
  },
  uploadedHeader: {
    fontSize: '1.1rem',
    margin: '0 0 15px 0',
    color: '#333'
  },
  fileList: {
    listStyleType: 'none',
    padding: 0,
    margin: 0
  },
  fileListItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 12px',
    backgroundColor: '#f8f9fa',
    border: '1px solid #eaeaea',
    borderRadius: '6px',
    marginBottom: '8px'
  },
  fileInfo: {
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    paddingRight: '10px'
  },
  fileName: {
    fontSize: '0.9rem',
    fontWeight: '500',
    color: '#333',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis'
  },
  fileSize: {
    fontSize: '0.8rem',
    color: '#666',
    marginTop: '2px'
  },
  deleteButton: {
    backgroundColor: '#fff',
    color: '#dc3545',
    border: '1px solid #dc3545',
    borderRadius: '4px',
    width: '28px',
    height: '28px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    fontWeight: 'bold',
    transition: 'all 0.2s'
  }
};

export default PdfUploadComponent;