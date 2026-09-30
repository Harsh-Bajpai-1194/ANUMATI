import express from 'express';
import path from 'path';
import apiRoutes from './controllers/routes.js';
import dotenv from 'dotenv';
import helmet from 'helmet';
import cors from 'cors';
import prisma from './config/db.js';
import connectMongoDB, { disconnectMongoDB } from './config/mongo.js';
import { resumeStuckEvaluations } from './services/evaluationQueue.js';

dotenv.config();

const app = express();
const port = process.env.PORT || 3000;

app.use(helmet());
app.use(cors({ origin: process.env.FRONTEND_URL || 'http://localhost:8080' }));
app.use(express.json({ limit: '2mb' }));

app.use('/uploads', express.static(path.resolve('uploads'))); 
app.use('/api', apiRoutes);

app.get('/', (req, res) => {
  res.send('Hello from the ANUMATI backend!');
});

const startServer = async () => {
  try {
    await connectMongoDB();
    await prisma.$connect();
    console.log('PostgreSQL Connected via Prisma');

    // Resume stuck evaluations on startup (Issue #85)
    await resumeStuckEvaluations();

    const server = app.listen(port, () => {
      console.log(`Server is listening on http://localhost:${port}`);
    });

    const shutdown = async () => {
      console.log('\nShutting down gracefully...');

      setTimeout(() => {
        console.error('Could not close connections in time, forcefully shutting down.');
        process.exit(1);
      }, 10000);

      server.close(async (err) => {
        console.log('HTTP server closed. Disconnecting databases...');
        try {
          await disconnectMongoDB();
          await prisma.$disconnect();
          console.log('Databases disconnected successfully.');
          process.exit(err ? 1 : 0);
        } catch (dbError) {
          console.error('Error during database disconnection:', dbError);
          process.exit(1);
        }
      });
    };

    process.on('SIGINT', shutdown);  
    process.on('SIGTERM', shutdown); 

  } catch (error) {
    console.error('Failed to initialize server:', error);
    process.exit(1);
  }
};

startServer();
