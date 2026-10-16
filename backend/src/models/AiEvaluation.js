import mongoose from 'mongoose';

const aiEvaluationSchema = new mongoose.Schema({
  applicationId: {
    type: String,
    index: true,
    sparse: true
  },
  documentId: {
    type: String,
    index: true,
    sparse: true
  },
  complianceScore: {
    type: Number,
    default: 0
  },
  extractedTextMetadata: {
    ocrConfidenceScore: Number,
    extractedEntities: { type: mongoose.Schema.Types.Mixed, default: {} }
  },
  anomalyDetection: {
    flagged: { type: Boolean, default: false },
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

aiEvaluationSchema.pre('validate', function() {
  if (!this.applicationId && !this.documentId) {
    this.invalidate('applicationId', 'Either applicationId or documentId is required.');
  }
});

const AiEvaluation = mongoose.model('AiEvaluation', aiEvaluationSchema);
export default AiEvaluation;
