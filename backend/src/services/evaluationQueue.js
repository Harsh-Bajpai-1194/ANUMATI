import fs from 'fs';
import path from 'path';
import prisma from '../config/db.js';
import { dispatchAiEvaluation } from './aiEvaluationService.js';

const CONCURRENCY_LIMIT = 2;
let activeCount = 0;

export const enqueueEvaluation = () => {
  setImmediate(processQueue);
};

const processQueue = async () => {
  if (activeCount >= CONCURRENCY_LIMIT) return;
  activeCount++;
  let claimed = false;

  try {
    // Find the oldest pending document in PostgreSQL (Issue #35)
    const doc = await prisma.document.findFirst({
      where: { status: 'uploaded' },
      orderBy: { createdAt: 'asc' }
    });

    if (!doc) return;

    // Atomically claim the job: only one worker can flip uploaded -> evaluating
    const { count } = await prisma.document.updateMany({
      where: { documentId: doc.documentId, status: 'uploaded' },
      data: { status: 'evaluating' }
    });

    if (count !== 1) return; // another worker claimed it
    claimed = true;

    const uploadDir = path.resolve('uploads');
    const safeFileName = path.basename(doc.storageKey);
    const resolvedPath = path.resolve(uploadDir, safeFileName);

    try {
      const evaluation = await dispatchAiEvaluation(doc.applicationId || 'standalone-doc', resolvedPath);
      await prisma.document.update({
        where: { documentId: doc.documentId },
        data: {
          status: 'evaluated',
          mongoAiEvaluationRef: evaluation?._id ? evaluation._id.toString() : null
        }
      });
    } catch (error) {
      console.error(`Evaluation failed for doc ${doc.documentId}:`, error);
      await prisma.document.update({
        where: { documentId: doc.documentId },
        data: { status: 'failed' }
      });
    }
  } catch (err) {
    console.error('Error in evaluation queue processing:', err);
  } finally {
    activeCount--;
    if (claimed) {
      setImmediate(processQueue);
    }
  }
};

export const resumeStuckEvaluations = async () => {
  try {
    const result = await prisma.document.updateMany({
      where: { status: 'evaluating' },
      data: { status: 'uploaded' }
    });
    if (result.count > 0) {
      console.log(`Re-queued ${result.count} stuck document evaluations.`);
      for (let i = 0; i < CONCURRENCY_LIMIT; i++) {
        setImmediate(processQueue);
      }
    }
  } catch (error) {
    console.error('Failed to resume stuck evaluations:', error);
  }
};
