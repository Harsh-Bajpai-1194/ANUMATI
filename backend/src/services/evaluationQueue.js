import fs from 'fs';
import path from 'path';
import prisma from '../config/db.js';
import { dispatchAiEvaluation } from './aiEvaluationService.js';
import { redisClient, deleteCached } from '../config/redis.js';
import { broadcastStatusTransition } from './realtimeService.js';

const CONCURRENCY_LIMIT = 2;
const REDIS_QUEUE_KEY = 'queue:document_evaluations';
let activeCount = 0;

/**
 * Enqueue evaluation job backed by Redis list with database fallback.
 */
export const enqueueEvaluation = async (jobDescriptor = null) => {
  try {
    if (redisClient && redisClient.status === 'ready') {
      if (jobDescriptor) {
        await redisClient.lpush(REDIS_QUEUE_KEY, JSON.stringify(jobDescriptor));
      } else {
        // Find latest pending documents and sync into Redis list
        const pending = await prisma.document.findMany({
          where: { status: 'uploaded' },
          select: { documentId: true, applicationId: true, storageKey: true },
          take: 10
        });
        for (const p of pending) {
          await redisClient.lpush(REDIS_QUEUE_KEY, JSON.stringify(p));
        }
      }
    }
  } catch (err) {
    console.warn('[Queue] Redis lpush error, defaulting to database queue:', err.message);
  }

  setImmediate(processQueue);
};

const processQueue = async () => {
  if (activeCount >= CONCURRENCY_LIMIT) return;
  activeCount++;
  let claimed = false;

  try {
    let targetDocId = null;

    // 1. Try popping next job from persistent Redis queue
    try {
      if (redisClient && redisClient.status === 'ready') {
        const rawJob = await redisClient.rpop(REDIS_QUEUE_KEY);
        if (rawJob) {
          const parsedJob = JSON.parse(rawJob);
          targetDocId = parsedJob.documentId;
        }
      }
    } catch (err) {
      console.warn('[Queue] Redis rpop error:', err.message);
    }

    // 2. Fetch document record (from Redis target or fallback to oldest uploaded doc in PostgreSQL)
    let doc = null;
    if (targetDocId) {
      doc = await prisma.document.findUnique({ where: { documentId: targetDocId } });
      // If already processed or invalid, continue
      if (!doc || doc.status !== 'uploaded') {
        doc = null;
      }
    }

    if (!doc) {
      doc = await prisma.document.findFirst({
        where: { status: 'uploaded' },
        orderBy: { createdAt: 'asc' }
      });
    }

    if (!doc) return;

    // Atomically claim the job in PostgreSQL: only one worker can flip uploaded -> evaluating
    const { count } = await prisma.document.updateMany({
      where: { documentId: doc.documentId, status: 'uploaded' },
      data: { status: 'evaluating' }
    });

    if (count !== 1) return; // another worker claimed it
    claimed = true;

    // Real-Time Broadcast: Document entered evaluation
    if (doc.applicationId) {
      await broadcastStatusTransition({
        type: 'STATUS_TRANSITION',
        applicationId: doc.applicationId,
        documentId: doc.documentId,
        status: 'Under AI Review',
        stage: 'processing',
        message: 'Document entered automated AI compliance evaluation.'
      });
    }

    const uploadDir = path.resolve('uploads');
    const safeFileName = path.basename(doc.storageKey);
    const resolvedPath = path.resolve(uploadDir, safeFileName);

    try {
      const evaluation = await dispatchAiEvaluation(
        {
          applicationId: doc.applicationId || null,
          documentId: doc.documentId
        },
        resolvedPath
      );

      await prisma.document.update({
        where: { documentId: doc.documentId },
        data: {
          status: 'evaluated',
          mongoAiEvaluationRef: evaluation?._id ? evaluation._id.toString() : null
        }
      });

      // Invalidate relevant Redis caches upon completion
      if (doc.applicationId) {
        await deleteCached(`cache:app:${doc.applicationId}`);
        await deleteCached(`cache:ai_eval:app:${doc.applicationId}`);

        // Real-Time Broadcast: Evaluation complete
        await broadcastStatusTransition({
          type: 'STATUS_TRANSITION',
          applicationId: doc.applicationId,
          documentId: doc.documentId,
          status: 'Under AI Review',
          stage: 'completed',
          complianceScore: evaluation?.complianceScore || 0,
          message: `Evaluation completed successfully with compliance score ${evaluation?.complianceScore || 0}%.`
        });
      }

    } catch (error) {
      console.error(`Evaluation failed for doc ${doc.documentId}:`, error);
      await prisma.document.update({
        where: { documentId: doc.documentId },
        data: { status: 'failed' }
      });

      if (doc.applicationId) {
        await broadcastStatusTransition({
          type: 'STATUS_TRANSITION',
          applicationId: doc.applicationId,
          documentId: doc.documentId,
          status: 'Evaluation Failed',
          stage: 'failed',
          message: 'Document evaluation encountered an error.'
        });
      }
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

/**
 * Resumes stuck evaluations on startup and synchronizes with Redis queue.
 */
export const resumeStuckEvaluations = async () => {
  try {
    const result = await prisma.document.updateMany({
      where: { status: 'evaluating' },
      data: { status: 'uploaded' }
    });

    if (result.count > 0) {
      console.log(`[Queue] Re-queued ${result.count} stuck document evaluations.`);
    }

    // Push pending documents to Redis persistent queue
    const pending = await prisma.document.findMany({
      where: { status: 'uploaded' },
      select: { documentId: true, applicationId: true, storageKey: true }
    });

    if (pending.length > 0 && redisClient && redisClient.status === 'ready') {
      try {
        await redisClient.del(REDIS_QUEUE_KEY);
        for (const p of pending) {
          await redisClient.lpush(REDIS_QUEUE_KEY, JSON.stringify(p));
        }
        console.log(`[Queue] Synced ${pending.length} pending jobs into Redis broker list.`);
      } catch (err) {
        console.warn('[Queue] Could not sync jobs to Redis:', err.message);
      }
    }

    for (let i = 0; i < CONCURRENCY_LIMIT; i++) {
      setImmediate(processQueue);
    }
  } catch (error) {
    console.error('Failed to resume stuck evaluations:', error);
  }
};
