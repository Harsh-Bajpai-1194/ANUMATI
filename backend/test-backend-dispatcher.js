import dotenv from 'dotenv';
import http from 'http';
import fs from 'fs';
import path from 'path';
import connectMongoDB, { disconnectMongoDB } from './src/config/mongo.js';
import { dispatchAiEvaluation } from './src/services/aiEvaluationService.js';
import AiEvaluation from './src/models/AiEvaluation.js';
import { ML_INTERNAL_TOKEN } from './src/config/auth.js';

dotenv.config();

const uploadDir = path.resolve('uploads');
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true });
}

const mockSuccessResponse = {
  success: true,
  document: { name: 'sample.pdf', sizeBytes: 1024, pageCount: 1 },
  classification: { category: 'AICTE_APPROVAL_LETTER', confidence: 0.95 },
  textExtraction: {
    ocrConfidenceScore: 0.92,
    method: 'DIRECT',
    totalWords: 120,
    extractedEntities: {
      institution_name: 'ANUMATI Test Engineering College',
      application_id: 'APP-DISPATCH-999'
    }
  },
  signatureVerification: {
    detected: true,
    stampDetected: true,
    confidenceScore: 0.89,
    status: 'VERIFIED'
  },
  complianceEvaluation: {
    overall_status: 'COMPLIANT',
    compliance_score: 0.85
  },
  complianceScore: 0.85,
  anomalyDetection: {
    flagged: false,
    flags: []
  },
  rawModelResponse: {
    document: { name: 'sample.pdf' }
  }
};

const runDispatcherTests = async () => {
  console.log('--- Starting Backend Dispatcher (Issue #30) Multipart Tests ---');

  let server;
  let serverPort;
  let lastReceivedHeaders = null;
  let lastReceivedBody = null;
  let simulateMode = 'success'; // 'success' | 'unauthorized' | 'server_error' | 'timeout'
  let savedRecordId = null;
  let savedStandaloneRecordId = null;

  const testPdfPath = path.resolve(uploadDir, `test-dispatch-${Date.now()}.pdf`);
  const dummyPdfContent = '%PDF-1.4\n%Test AICTE Document for Multipart Dispatcher\n%%EOF';
  fs.writeFileSync(testPdfPath, dummyPdfContent);

  try {
    await connectMongoDB();

    // Spin up mock ML Service
    server = http.createServer((req, res) => {
      lastReceivedHeaders = req.headers;
      const chunks = [];

      req.on('data', (chunk) => chunks.push(chunk));
      req.on('end', () => {
        lastReceivedBody = Buffer.concat(chunks).toString('utf-8');

        if (simulateMode === 'timeout') {
          // Do not reply, let caller timeout
          return;
        }

        if (simulateMode === 'unauthorized') {
          res.writeHead(401, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ detail: 'Unauthorized: Missing or invalid X-Internal-Token header.' }));
          return;
        }

        if (simulateMode === 'server_error') {
          res.writeHead(500, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ detail: 'Internal ML evaluation failure.' }));
          return;
        }

        // Default: 200 OK
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(mockSuccessResponse));
      });
    });

    await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
    serverPort = server.address().port;
    process.env.ML_SERVICE_URL = `http://127.0.0.1:${serverPort}`;

    console.log(`✓ Mock ML service listening on port ${serverPort}`);

    // TEST 1: Dispatches binary file as multipart/form-data with auth token
    console.log('\n1. Testing multipart file streaming and headers...');
    simulateMode = 'success';
    const testAppId = `APP-DISPATCH-${Date.now()}`;
    const result = await dispatchAiEvaluation(testAppId, testPdfPath);
    savedRecordId = result._id;

    if (!lastReceivedHeaders['content-type']?.includes('multipart/form-data; boundary=')) {
      throw new Error(`Expected multipart/form-data Content-Type header with boundary, got: "${lastReceivedHeaders['content-type']}"`);
    }
    console.log(`   ✓ Content-Type contains multipart boundary: "${lastReceivedHeaders['content-type'].split(';')[0]}"`);

    if (lastReceivedHeaders['x-internal-token'] !== ML_INTERNAL_TOKEN) {
      throw new Error(`Expected X-Internal-Token header "${ML_INTERNAL_TOKEN}", got: "${lastReceivedHeaders['x-internal-token']}"`);
    }
    console.log(`   ✓ X-Internal-Token header authenticated properly.`);

    if (!lastReceivedBody.includes('name="file"') || !lastReceivedBody.includes('%PDF-1.4')) {
      throw new Error('Multipart body does not contain file form-data part or PDF magic bytes.');
    }
    console.log(`   ✓ Verified file stream: body contains 'name="file"' and raw PDF bytes.`);

    if (!result || result.applicationId !== testAppId) {
      throw new Error('dispatchAiEvaluation did not return saved MongoDB record.');
    }
    console.log(`   ✓ Result saved to MongoDB with _id: ${result._id}`);

    // TEST 1b: Standalone document evaluation with documentId only (CodeRabbit feedback)
    console.log('\n1b. Testing standalone document evaluation (documentId only, applicationId unset)...');
    const testDocId = `DOC-STANDALONE-${Date.now()}`;
    const standaloneResult = await dispatchAiEvaluation({ documentId: testDocId }, testPdfPath);
    savedStandaloneRecordId = standaloneResult._id;

    if (!standaloneResult || standaloneResult.documentId !== testDocId) {
      throw new Error(`Expected saved record documentId "${testDocId}", got "${standaloneResult?.documentId}"`);
    }
    if (standaloneResult.applicationId) {
      throw new Error(`Expected applicationId to be unset for standalone document, got "${standaloneResult.applicationId}"`);
    }
    console.log(`   ✓ Standalone document saved with documentId: ${standaloneResult.documentId} and applicationId: unset.`);

    // TEST 2: Local file not found throws error before network request
    console.log('\n2. Testing missing local file error handling...');
    let threwForMissing = false;
    try {
      await dispatchAiEvaluation('APP-TEST-MISSING', path.resolve(uploadDir, 'non-existent-file.pdf'));
    } catch (err) {
      if (err.message.includes('File not found')) {
        threwForMissing = true;
        console.log(`   ✓ Properly threw error: "${err.message}"`);
      } else {
        throw err;
      }
    }
    if (!threwForMissing) {
      throw new Error('Should have thrown error for non-existent file.');
    }

    // TEST 3: ML service returns 401 Unauthorized
    console.log('\n3. Testing 401 Unauthorized handling from ML Service...');
    simulateMode = 'unauthorized';
    let threwFor401 = false;
    try {
      await dispatchAiEvaluation('APP-TEST-401', testPdfPath);
    } catch (err) {
      if (err.message.includes('Unauthorized')) {
        threwFor401 = true;
        console.log(`   ✓ Properly propagated ML error: "${err.message}"`);
      } else {
        throw err;
      }
    }
    if (!threwFor401) {
      throw new Error('Should have thrown error for 401 from ML Service.');
    }

    // TEST 4: ML service returns 500 error
    console.log('\n4. Testing 500 Server Error handling from ML Service...');
    simulateMode = 'server_error';
    let threwFor500 = false;
    try {
      await dispatchAiEvaluation('APP-TEST-500', testPdfPath);
    } catch (err) {
      if (err.message.includes('Internal ML evaluation failure')) {
        threwFor500 = true;
        console.log(`   ✓ Properly propagated 500 detail: "${err.message}"`);
      } else {
        throw err;
      }
    }
    if (!threwFor500) {
      throw new Error('Should have thrown error for 500 from ML Service.');
    }

    console.log('\n======================================================');
    console.log('  ALL BACKEND DISPATCHER TESTS PASSED (100%)');
    console.log('======================================================');
  } catch (err) {
    console.error('\n❌ Test failed:', err);
    process.exitCode = 1;
  } finally {
    if (savedRecordId) {
      try {
        await AiEvaluation.deleteOne({ _id: savedRecordId });
        console.log(`✓ Cleanup: Removed temporary MongoDB record ${savedRecordId}.`);
      } catch (cleanErr) {
        console.warn('Warning: Failed to clean up MongoDB record:', cleanErr.message);
      }
    }
    if (savedStandaloneRecordId) {
      try {
        await AiEvaluation.deleteOne({ _id: savedStandaloneRecordId });
        console.log(`✓ Cleanup: Removed temporary MongoDB record ${savedStandaloneRecordId}.`);
      } catch (cleanErr) {
        console.warn('Warning: Failed to clean up MongoDB standalone record:', cleanErr.message);
      }
    }
    if (fs.existsSync(testPdfPath)) {
      try {
        fs.unlinkSync(testPdfPath);
        console.log('✓ Cleanup: Removed temporary test PDF file.');
      } catch (e) {
        console.warn('Warning: Failed to remove temporary PDF:', e.message);
      }
    }
    if (server) {
      server.close();
    }
    await disconnectMongoDB();
  }
};

runDispatcherTests();

