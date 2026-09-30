import mongoose from 'mongoose';

const documentSchema = new mongoose.Schema({
  applicationId: { type: String, required: true, index: true },
  originalName: { type: String, required: true },
  storedName: { type: String, required: true },
  filePath: { type: String, required: true },
  sizeBytes: { type: Number, required: true },
  mimetype: { type: String, required: true },
  status: { 
    type: String, 
    enum: ['uploaded', 'evaluating', 'evaluated', 'failed'], 
    default: 'uploaded' 
  },
  failureReason: { type: String },
  aiEvaluationId: { type: mongoose.Schema.Types.ObjectId, ref: 'AiEvaluation' }
}, { timestamps: true });

export default mongoose.model('Document', documentSchema);
