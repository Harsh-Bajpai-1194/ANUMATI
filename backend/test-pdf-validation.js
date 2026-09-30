import express from 'express';
import fs from 'fs';
import { uploadPdf, validatePdfContent } from './src/middleware/middleware.js';

const app = express();

app.post('/api/documents/upload-test', (req, res, next) => {
  uploadPdf.single('file')(req, res, (err) => {
    if (err) return res.status(400).json({ success: false, message: err.message });
    next();
  });
}, validatePdfContent, (req, res) => {
  res.status(201).json({
    success: true,
    message: 'Valid PDF accepted.',
    filename: req.file.filename
  });
  // Cleanup valid uploaded test file from disk
  if (req.file && fs.existsSync(req.file.path)) {
    fs.unlinkSync(req.file.path);
  }
});

const runTests = async () => {
  console.log('--- Starting PDF Content Validation Security Tests ---');

  const server = app.listen(0);
  const port = server.address().port;
  const targetUrl = `http://127.0.0.1:${port}/api/documents/upload-test`;

  try {
    // -------------------------------------------------------------
    // Test 1: Non-PDF file with spoofed application/pdf header -> 400 + file removed
    // -------------------------------------------------------------
    console.log('\n1. Testing non-PDF with spoofed application/pdf MIME type...');
    const fakeFormData = new FormData();
    const fakeContent = '<html><body><h1>Not a real PDF!</h1></body></html>';
    fakeFormData.append('file', new Blob([fakeContent], { type: 'application/pdf' }), 'renamed_executable.pdf');

    const res1 = await fetch(targetUrl, { method: 'POST', body: fakeFormData });
    const data1 = await res1.json();

    console.log(`   ✓ Received Status: ${res1.status} (Expected: 400)`);
    console.log(`   ✓ Error Message: "${data1.message}"`);
    if (res1.status !== 400) {
      throw new Error(`Expected status 400 for spoofed PDF, but received ${res1.status}`);
    }

    // Verify file was purged from disk
    const leftoverFiles = fs.readdirSync('uploads').filter(f => f.endsWith('renamed_executable.pdf'));
    if (leftoverFiles.length > 0) {
      throw new Error('Security Failure: Invalid file was not deleted from disk!');
    }
    console.log('   ✓ Verified: Spoofed file was completely purged from uploads/ disk directory.');

    // -------------------------------------------------------------
    // Test 2: Valid PDF with %PDF- header -> 201
    // -------------------------------------------------------------
    console.log('\n2. Testing genuine PDF with %PDF- magic bytes...');
    const validFormData = new FormData();
    const validPdfContent = '%PDF-1.4\n%âãÏÓ\n1 0 obj\n<< /Title (Test Valid PDF) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF';
    validFormData.append('file', new Blob([validPdfContent], { type: 'application/pdf' }), 'genuine.pdf');

    const res2 = await fetch(targetUrl, { method: 'POST', body: validFormData });
    const data2 = await res2.json();

    console.log(`   ✓ Received Status: ${res2.status} (Expected: 201)`);
    console.log(`   ✓ Success: ${data2.success}`);
    if (res2.status !== 201 || !data2.success) {
      throw new Error(`Expected status 201 for valid PDF, but received ${res2.status}`);
    }

    console.log('\n=============================================================');
    console.log('  ALL PDF CONTENT VALIDATION TESTS PASSED (100%)');
    console.log('=============================================================');
  } catch (err) {
    console.error('\n❌ PDF Content Validation Test Failed:', err);
    process.exitCode = 1;
  } finally {
    server.close();
  }
};

runTests();
