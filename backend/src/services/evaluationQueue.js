import Document from '../models/Document.js';
import { dispatchAiEvaluation } from './aiEvaluationService.js';

const CONCURRENCY_LIMIT = 2;
let activeCount = 0;

export const enqueueEvaluation = () => {
  setImmediate(processQueue);
};

const processQueue = async () => {
  if (activeCount >= CONCURRENCY_LIMIT) return;

  // Find the oldest pending document and mark it as evaluating
  const doc = await Document.findOneAndUpdate(
    { status: 'uploaded' },
    { $set: { status: 'evaluating' } },
    { sort: { createdAt: 1 }, returnDocument: 'after' }
  );

  if (!doc) return;

  activeCount++;
  
  try {
    const evaluation = await dispatchAiEvaluation(doc.applicationId, doc.filePath);
    await Document.updateOne(
      { _id: doc._id },
      { $set: { status: 'evaluated', aiEvaluationId: evaluation._id } }
    );
  } catch (error) {
    console.error(`Evaluation failed for doc ${doc._id}:`, error);
    await Document.updateOne(
      { _id: doc._id },
      { $set: { status: 'failed', failureReason: error.message } }
    );
  } finally {
    activeCount--;
    // Immediately check if there are more jobs pending in the queue
    setImmediate(processQueue);
  }
};

export const resumeStuckEvaluations = async () => {
  try {
    const result = await Document.updateMany(
      { status: 'evaluating' },
      { $set: { status: 'uploaded' } }
    );
    if (result.modifiedCount > 0) {
      console.log(`Re-queued ${result.modifiedCount} stuck document evaluations.`);
      for (let i = 0; i < CONCURRENCY_LIMIT; i++) {
        setImmediate(processQueue);
      }
    }
  } catch (error) {
    console.error('Failed to resume stuck evaluations:', error);
  }
};
