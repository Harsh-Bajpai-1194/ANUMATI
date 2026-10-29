import Redis from 'ioredis';
import dotenv from 'dotenv';

dotenv.config();

const REDIS_URL = process.env.REDIS_URL || 'redis://127.0.0.1:6379';

// In-memory fallback cache for environments without a running Redis server
const memoryCache = new Map();

let redisClient = null;
let redisPub = null;
let redisSub = null;
let isRedisConnected = false;

try {
  const redisOptions = {
    maxRetriesPerRequest: 1,
    retryStrategy: (times) => {
      if (times > 3) {
        return null; // Stop retrying after 3 attempts in local/dev to avoid spamming logs
      }
      return Math.min(times * 200, 1000);
    },
    enableOfflineQueue: false,
    lazyConnect: true
  };

  redisClient = new Redis(REDIS_URL, redisOptions);
  redisPub = new Redis(REDIS_URL, redisOptions);
  redisSub = new Redis(REDIS_URL, redisOptions);

  redisClient.on('connect', () => {
    isRedisConnected = true;
    console.log('[Redis Cache] Connected to Redis at', REDIS_URL);
  });

  redisClient.on('error', (err) => {
    isRedisConnected = false;
    // Log once, suppress repeated network loop errors when Redis is not running
    if (err.code === 'ECONNREFUSED') {
      // In-memory fallback active
    } else {
      console.warn('[Redis Cache] Redis warning:', err.message);
    }
  });

  redisSub.on('error', () => {});
  redisPub.on('error', () => {});

} catch (initError) {
  console.warn('[Redis Cache] Could not initialize Redis client, using in-memory cache:', initError.message);
}

export const connectRedis = async () => {
  if (!redisClient) return false;
  try {
    await redisClient.connect().catch(() => {});
    await redisPub.connect().catch(() => {});
    await redisSub.connect().catch(() => {});
    return isRedisConnected;
  } catch {
    return false;
  }
};

export const disconnectRedis = async () => {
  try {
    if (redisClient && redisClient.status === 'ready') await redisClient.quit();
    if (redisPub && redisPub.status === 'ready') await redisPub.quit();
    if (redisSub && redisSub.status === 'ready') await redisSub.quit();
  } catch (err) {
    console.error('[Redis Cache] Error disconnecting Redis:', err.message);
  }
};

/**
 * Get value from Redis cache with in-memory fallback
 */
export const getCached = async (key) => {
  try {
    if (isRedisConnected && redisClient && redisClient.status === 'ready') {
      const data = await redisClient.get(key);
      return data ? JSON.parse(data) : null;
    }
  } catch (err) {
    console.warn(`[Redis Cache] getCached error for key ${key}:`, err.message);
  }

  // Fallback to in-memory cache
  const item = memoryCache.get(key);
  if (!item) return null;
  if (item.expiry && Date.now() > item.expiry) {
    memoryCache.delete(key);
    return null;
  }
  return item.value;
};

/**
 * Set value in Redis cache with in-memory fallback
 */
export const setCached = async (key, value, ttlSeconds = 120) => {
  try {
    if (isRedisConnected && redisClient && redisClient.status === 'ready') {
      await redisClient.set(key, JSON.stringify(value), 'EX', ttlSeconds);
      return true;
    }
  } catch (err) {
    console.warn(`[Redis Cache] setCached error for key ${key}:`, err.message);
  }

  // Fallback to in-memory cache
  memoryCache.set(key, {
    value,
    expiry: ttlSeconds ? Date.now() + ttlSeconds * 1000 : null
  });
  return true;
};

/**
 * Delete key from cache
 */
export const deleteCached = async (key) => {
  try {
    if (isRedisConnected && redisClient && redisClient.status === 'ready') {
      await redisClient.del(key);
    }
  } catch (err) {
    console.warn(`[Redis Cache] deleteCached error for key ${key}:`, err.message);
  }
  memoryCache.delete(key);
};

/**
 * Invalidate all keys matching a prefix or pattern
 */
export const invalidatePattern = async (pattern) => {
  try {
    if (isRedisConnected && redisClient && redisClient.status === 'ready') {
      const keys = await redisClient.keys(pattern);
      if (keys.length > 0) {
        await redisClient.del(...keys);
      }
    }
  } catch (err) {
    console.warn(`[Redis Cache] invalidatePattern error for pattern ${pattern}:`, err.message);
  }

  for (const k of memoryCache.keys()) {
    if (k.startsWith(pattern.replace('*', ''))) {
      memoryCache.delete(k);
    }
  }
};

export { redisClient, redisPub, redisSub, isRedisConnected };
export default redisClient;

