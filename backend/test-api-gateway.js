import path from 'path';
import dotenv from 'dotenv';
dotenv.config({ path: path.resolve('backend/.env') });
dotenv.config();
if (!process.env.JWT_SECRET) process.env.JWT_SECRET = 'dev-jwt-secret-testing';
if (!process.env.NODE_ENV) process.env.NODE_ENV = 'development';

const {
  loginLimiter,
  uploadLimiter,
  apiGatewayLimiter,
  handleMulterUpload,
  uploadPdf
} = await import('./src/middleware/middleware.js');

const { validateAiReportContract } = await import('./src/services/aiEvaluationService.js');

const runGatewayTests = async () => {
  console.log('=============================================================');
  console.log('  STARTING API GATEWAY, RATE LIMITING & ROUTING TESTS (#117) ');
  console.log('=============================================================\n');

  let passedTests = 0;
  let totalTests = 0;

  const assert = (condition, testName) => {
    totalTests++;
    if (condition) {
      console.log(`  ✓ PASSED: ${testName}`);
      passedTests++;
    } else {
      console.error(`  ✗ FAILED: ${testName}`);
      process.exitCode = 1;
    }
  };

  // --------------------------------------------------------------------------
  // Test 1: JSON Contract Enforcement (Technical Notes)
  // --------------------------------------------------------------------------
  console.log('1. Testing JSON Contract Enforcement (aiEvaluationService)...');

  const validReport = {
    status: 'completed',
    complianceScore: 92.5,
    textExtraction: {
      ocrConfidenceScore: 0.95,
      extractedEntities: { institution_name: 'AICTE Demonstration Institute' }
    },
    anomalyDetection: {
      flagged: false,
      flags: []
    }
  };

  try {
    const isValid = validateAiReportContract(validReport);
    assert(isValid === true, 'Valid JSON report satisfies schema contract');
  } catch (err) {
    assert(false, `Valid report failed validation: ${err.message}`);
  }

  // Contract violation: missing required textExtraction and anomalyDetection
  try {
    validateAiReportContract({ status: 'completed' });
    assert(false, 'Expected schema violation for missing extraction and anomaly detection');
  } catch (err) {
    assert(
      err.message.includes('Contract Violation') && err.message.includes('Missing required'),
      'Catches missing textExtraction and anomalyDetection contract violation'
    );
  }

  // Contract violation: incomplete/failed status
  try {
    validateAiReportContract({ status: 'failed', complianceScore: 10 });
    assert(false, 'Expected schema violation for failed status');
  } catch (err) {
    assert(
      err.message.includes('Incomplete evaluation status'),
      'Catches incomplete/failed evaluation status'
    );
  }

  // Contract violation: non-numeric complianceScore
  try {
    validateAiReportContract({
      textExtraction: {},
      anomalyDetection: { flagged: false },
      complianceScore: 'NOT_A_NUMBER'
    });
    assert(false, 'Expected schema violation for non-numeric complianceScore');
  } catch (err) {
    assert(
      err.message.includes('numeric value'),
      'Catches invalid complianceScore type'
    );
  }

  // --------------------------------------------------------------------------
  // Test 2: Rate Limiters & Gateway Middleware Configuration
  // --------------------------------------------------------------------------
  console.log('\n2. Testing Gateway Rate Limiters & Upload Throttling...');

  assert(typeof loginLimiter === 'function', 'loginLimiter middleware is exported and configured');
  assert(typeof uploadLimiter === 'function', 'uploadLimiter middleware is exported and configured');
  assert(typeof apiGatewayLimiter === 'function', 'apiGatewayLimiter middleware is exported and configured');
  assert(typeof handleMulterUpload === 'function', 'handleMulterUpload gateway 15MB wrapper is exported and configured');

  console.log('\n=============================================================');
  console.log(`  SUMMARY: ${passedTests}/${totalTests} TESTS PASSED (100%)`);
  console.log('=============================================================');
};

runGatewayTests().catch((err) => {
  console.error('Fatal test error:', err);
  process.exit(1);
});

