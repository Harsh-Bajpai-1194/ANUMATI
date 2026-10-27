import { redisPub, redisSub, isRedisConnected } from '../config/redis.js';

const REALTIME_CHANNEL = 'anumati:realtime:events';

// Active connected SSE clients: Set of Express response objects
const sseClients = new Set();

let isSubscribedToRedis = false;

/**
 * Initializes Redis Pub/Sub subscriber to broadcast messages across cluster instances.
 */
export const initRealtimeSubscriber = () => {
  if (!redisSub || isSubscribedToRedis) return;

  try {
    redisSub.subscribe(REALTIME_CHANNEL, (err) => {
      if (!err) {
        isSubscribedToRedis = true;
        console.log('[Real-time SSE] Subscribed to Redis channel:', REALTIME_CHANNEL);
      }
    });

    redisSub.on('message', (channel, message) => {
      if (channel === REALTIME_CHANNEL) {
        try {
          const parsed = JSON.parse(message);
          dispatchToLocalClients(parsed);
        } catch {
          // ignore malformed payloads
        }
      }
    });
  } catch (err) {
    console.warn('[Real-time SSE] Redis subscriber initialization skipped:', err.message);
  }
};

/**
 * Dispatches a formatted SSE event payload to all currently connected local clients.
 */
const dispatchToLocalClients = (eventData) => {
  if (sseClients.size === 0) return;

  const sseMessage = `event: status_update\ndata: ${JSON.stringify(eventData)}\n\n`;

  for (const client of sseClients) {
    try {
      client.write(sseMessage);
    } catch {
      sseClients.delete(client);
    }
  }
};

/**
 * Broadcasts an application status update across all instances and clients.
 * @param {Object} eventData e.g. { applicationId, documentId, status, timestamp, details }
 */
export const broadcastStatusTransition = async (eventData) => {
  const payload = {
    ...eventData,
    timestamp: eventData.timestamp || new Date().toISOString()
  };

  // 1. Dispatch immediately to local SSE connections
  dispatchToLocalClients(payload);

  // 2. Publish to Redis channel so other horizontal container instances receive it
  try {
    if (redisPub && redisPub.status === 'ready') {
      await redisPub.publish(REALTIME_CHANNEL, JSON.stringify(payload));
    }
  } catch (err) {
    console.warn('[Real-time SSE] Could not publish event to Redis:', err.message);
  }
};

/**
 * Handles incoming SSE connection requests (/api/events/subscribe).
 */
export const handleSseSubscription = (req, res) => {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache, no-transform',
    'Connection': 'keep-alive',
    'X-Accel-Buffering': 'no' // Instructs Nginx not to buffer SSE stream
  });

  // Initial connection handshake
  res.write(': connected\n');
  res.write(`event: connected\ndata: ${JSON.stringify({ message: 'Connected to ANUMATI Real-Time Event Stream' })}\n\n`);

  sseClients.add(res);

  // Periodically send a heartbeat comment every 25 seconds to keep the connection alive
  const heartbeatInterval = setInterval(() => {
    try {
      res.write(': ping\n\n');
    } catch {
      clearInterval(heartbeatInterval);
      sseClients.delete(res);
    }
  }, 25000);

  req.on('close', () => {
    clearInterval(heartbeatInterval);
    sseClients.delete(res);
  });
};

/**
 * Returns count of active SSE client connections
 */
export const getActiveConnectionCount = () => sseClients.size;

