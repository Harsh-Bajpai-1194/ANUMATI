import mongoose from 'mongoose';

const aiEvaluationSchema = new mongoose.Schema({
  applicationId: {
    type: String,
    required: true,
    index: true
    // NOTE: This is a reference to the Application ID in PostgreSQL.
    // Ensure integrity at the API routing level.
  },
  extractedTextMetadata: {
    ocrConfidenceScore: Number,
    extractedEntities: { type: mongoose.Schema.Types.Mixed, default: {} }
  },
  anomalyDetection: {
    flagged: { type: Boolean, default: false },
    confidence: Number,
    flags: [{
      ruleCode: String,
      description: String,
      severity: { type: String, enum: ['low', 'medium', 'high', 'critical'] }
    }]
  },
  rawModelResponse: { type: mongoose.Schema.Types.Mixed }
}, {
  timestamps: true
});

const AiEvaluation = mongoose.model('AiEvaluation', aiEvaluationSchema);
export default AiEvaluation;