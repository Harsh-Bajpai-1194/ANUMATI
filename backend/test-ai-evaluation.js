import dotenv from 'dotenv';
import mongoose from 'mongoose';
import connectMongoDB, { disconnectMongoDB } from './src/config/mongo.js';
import {
  parseAndStoreAiReport,
  getAiEvaluationByApplicationId,
  getAiEvaluationById
} from './src/services/aiEvaluationService.js';
import AiEvaluation from './src/models/AiEvaluation.js';

dotenv.config();

const sampleMlReport = {
  documentId: 'TEST-APP-2026-001',
  status: 'completed',
  documentClassification: {
    predictedType: 'LOA',
    confidence: 0.96
  },
  textExtraction: {
    totalCharacters: 4500,
    pagesProcessed: 3,
    ocrApplied: false,
    extractionQualityScore: 0.94,
    extractedEntities: {
      institution_name: 'AICTE Demonstration Institute',
      application_id: 'TEST-APP-2026-001',
      land_area: 8.5,
      student_faculty_ratio: '15:1',
      has_anti_ragging_committee: true
    }
  },
  anomalyDetection: {
    flagged: true,
    confidence: 0.91,
    flags: [
      {
        ruleCode: 'RULE_LAND_DEFICIT',
        description: 'Land area of 8.5 acres is below the required 10.0 acres.',
        severity: 'high'
      },
      {
        ruleCode: 'RULE_FACULTY_CADRE_RATIO',
        description: 'Cadre ratio advisory: Professor to Assistant Professor ratio is uneven.',
        severity: 'medium'
      }
    ]
  },
  complianceSummary: {
    totalRulesEvaluated: 5,
    compliantCount: 4,
    nonCompliantCount: 1,
    complianceScore: 0.8
  }
};

const runVerification = async () => {
  console.log('--- Starting AI Evaluation Verification Test ---');

  let savedRecordId = null;

  try {
    await connectMongoDB();

    const testAppId = `APP-VERIFY-${Date.now()}`;

    // 1. Test parsing & storing
    console.log(`\n1. Storing sample AI evaluation report for: ${testAppId}`);
    const stored = await parseAndStoreAiReport(testAppId, sampleMlReport);
    savedRecordId = stored._id;
    console.log(`   ✓ Saved document with MongoDB _id: ${stored._id}`);
    console.log(`   ✓ OCR Score: ${stored.extractedTextMetadata.ocrConfidenceScore}`);
    console.log(`   ✓ Anomaly Flagged: ${stored.anomalyDetection.flagged}`);
    console.log(`   ✓ Flags Count: ${stored.anomalyDetection.flags.length}`);

    // 2. Test querying by applicationId
    console.log(`\n2. Querying reports for applicationId: ${testAppId}`);
    const records = await getAiEvaluationByApplicationId(testAppId);
    console.log(`   ✓ Found ${records.length} record(s)`);
    if (records.length === 0 || records[0].applicationId !== testAppId) {
      throw new Error('Query by applicationId failed to match record.');
    }

    // 3. Test querying by MongoDB ObjectId
    console.log(`\n3. Querying report by Mongo _id: ${stored._id}`);
    const single = await getAiEvaluationById(stored._id.toString());
    console.log(`   ✓ Retrieved record for: ${single.applicationId}`);

    // 4. Test error handling for missing applicationId
    console.log('\n4. Testing validation for missing applicationId');
    let rejectedAsExpected = false;
    try {
      await parseAndStoreAiReport('', sampleMlReport);
    } catch (err) {
      if (err.message.includes('valid applicationId')) {
        rejectedAsExpected = true;
        console.log(`   ✓ Properly rejected missing applicationId: "${err.message}"`);
      } else {
        throw err;
      }
    }
    if (!rejectedAsExpected) {
      throw new Error('Should have thrown validation error for empty applicationId');
    }

    // 5. Test rejection of empty / incomplete reports
    console.log('\n5. Testing validation for empty / incomplete report object');
    let incompleteRejected = false;
    try {
      await parseAndStoreAiReport(testAppId, {});
    } catch (err) {
      if (err.message.includes('Missing required')) {
        incompleteRejected = true;
        console.log(`   ✓ Properly rejected empty report: "${err.message}"`);
      } else {
        throw err;
      }
    }
    if (!incompleteRejected) {
      throw new Error('Should have rejected empty report object');
    }

    console.log('\n========================================');
    console.log('  ALL AI EVALUATION TESTS PASSED (100%)');
    console.log('========================================');
  } catch (error) {
    console.error('\n❌ Test failed:', error);
    process.exitCode = 1;
  } finally {
    // Cleanup temporary record even if assertions failed
    if (savedRecordId) {
      try {
        await AiEvaluation.deleteOne({ _id: savedRecordId });
        console.log(`\n✓ Cleanup: Removed temporary test document ${savedRecordId}.`);
      } catch (cleanupErr) {
        console.warn('⚠️ Warning: Failed to clean up test document:', cleanupErr.message);
      }
    }
    await disconnectMongoDB();
  }
};

runVerification();