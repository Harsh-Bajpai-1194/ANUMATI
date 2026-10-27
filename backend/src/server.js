import express from 'express';
import dotenv from 'dotenv';
import helmet from 'helmet';
import cors from 'cors';
import mongoose from 'mongoose';
import apiRoutes from '../api/routes.js';
import prisma from './config/db.js';
import connectMongoDB, { disconnectMongoDB } from './config/mongo.js';
import { connectRedis, disconnectRedis, isRedisConnected } from './config/redis.js';
import { initRealtimeSubscriber } from './services/realtimeService.js';
import { resumeStuckEvaluations } from './services/evaluationQueue.js';

dotenv.config();

const app = express();
const port = process.env.PORT || 5000;

// Security Headers
app.use(helmet());

// Production-Hardened CORS Configuration
const allowedOrigins = [
  process.env.FRONTEND_URL,
  'http://localhost:8080',
  'http://localhost:5173',
  'http://localhost:3000',
  'http://127.0.0.1:8080',
  'http://127.0.0.1:5173',
  'http://127.0.0.1:3000'
].filter(Boolean);

const corsOptions = {
  origin: (origin, callback) => {
    // Allow non-browser requests (e.g. internal server requests, health checks, curl)
    if (!origin || allowedOrigins.includes(origin) || process.env.NODE_ENV !== 'production') {
      return callback(null, true);
    }
    return callback(new Error('CORS policy: This origin is not allowed by Access-Control-Allow-Origin.'));
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin']
};

app.use(cors(corsOptions));
app.use(express.json({ limit: '2mb' }));

// ============================================================================
// Load Balancer Health Checks (Issue #117, #118)
// ============================================================================

// Liveness Probe: Verifies HTTP server is responding
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'UP',
    service: 'ANUMATI Express API Gateway',
    timestamp: new Date().toISOString()
  });
});

// Readiness Probe: Verifies database and cache connectivity
app.get('/ready', async (req, res) => {
  let isMongoReady = false;
  let isPostgresReady = false;

  try {
    isMongoReady = mongoose.connection.readyState === 1;
  } catch {
    isMongoReady = false;
  }

  try {
    await prisma.$queryRaw`SELECT 1`;
    isPostgresReady = true;
  } catch {
    isPostgresReady = false;
  }

  const isReady = isMongoReady && isPostgresReady;
  const statusCode = isReady ? 200 : 503;

  return res.status(statusCode).json({
    status: isReady ? 'UP' : 'DOWN',
    ready: isReady,
    databases: {
      mongodb: isMongoReady ? 'connected' : 'disconnected',
      postgres: isPostgresReady ? 'connected' : 'disconnected',
      redis: isRedisConnected ? 'connected' : 'in-memory-fallback'
    },
    uptime: Math.floor(process.uptime()),
    timestamp: new Date().toISOString()
  });
});

// Root welcome route
app.get('/', (req, res) => {
  res.send('Hello from the ANUMATI backend!');
});

// Centralized Gateway Routing
app.use('/api', apiRoutes);

// ============================================================================
// Standardized Gateway Error Responses (Issue #117)
// ============================================================================

// 404 Route Not Found Handler
app.use((req, res) => {
  res.status(404).json({
    success: false,
    message: `Resource not found on gateway: ${req.method} ${req.originalUrl}`
  });
});

// Centralized Gateway Error Handler
app.use((err, req, res, next) => {
  if (err.message && err.message.includes('CORS')) {
    return res.status(403).json({
      success: false,
      message: err.message
    });
  }

  if (err instanceof SyntaxError && err.status === 400 && 'body' in err) {
    return res.status(400).json({
      success: false,
      message: 'Malformed JSON payload provided in request.'
    });
  }

  if (err.code === 'LIMIT_FILE_SIZE') {
    return res.status(413).json({
      success: false,
      message: 'Payload too large: File exceeds the 15MB gateway limit.'
    });
  }

  const statusCode = err.statusCode || err.status || 500;
  const isDev = process.env.NODE_ENV !== 'production';

  res.status(statusCode).json({
    success: false,
    message: err.message || 'Internal server error.',
    ...(isDev && { stack: err.stack })
  });
});

const startServer = async () => {
  try {
    await connectMongoDB();
    await prisma.$connect();
    console.log('PostgreSQL Connected via Prisma');

    await connectRedis();
    initRealtimeSubscriber();

    await resumeStuckEvaluations();

    const server = app.listen(port, () => {
      console.log(`API Gateway is listening on http://localhost:${port}`);
    });

    const shutdown = async () => {
      console.log('\nShutting down gracefully...');

      setTimeout(() => {
        console.error('Could not close connections in time, forcefully shutting down.');
        process.exit(1);
      }, 10000);

      server.close(async (err) => {
        console.log('HTTP server closed. Disconnecting databases and caches...');
        try {
          await disconnectMongoDB();
          await prisma.$disconnect();
          await disconnectRedis();
          console.log('Databases and caches disconnected successfully.');
          process.exit(err ? 1 : 0);
        } catch (dbError) {
          console.error('Error during disconnection:', dbError);
          process.exit(1);
        }
      });
    };

    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);

  } catch (error) {
    console.error('Failed to initialize API Gateway server:', error);
    process.exit(1);
  }
};

startServer();

export default app;

export default app;