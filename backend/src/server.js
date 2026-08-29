import express from 'express';
import dotenv from 'dotenv';
import helmet from 'helmet';
import cors from 'cors';
import prisma from './config/db.js';
import connectMongoDB, { disconnectMongoDB } from './config/mongo.js';

dotenv.config();

const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(helmet());
app.use(cors({ origin: process.env.FRONTEND_URL }));
app.use(express.json({ limit: '2mb' }));

app.get('/', (req, res) => {
  res.send('Hello from the ANUMATI backend!');
});

const startServer = async () => {
  try {
    await connectMongoDB();
    await prisma.$connect();
    console.log('PostgreSQL Connected via Prisma');

    const server = app.listen(port, () => {
      console.log(`Server is listening on http://localhost:${port}`);
    });

    // Graceful Shutdown Logic
    const shutdown = async () => {
      console.log('\nShutting down gracefully...');

      // Force shutdown if requests take longer than 10 seconds to finish
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

    process.on('SIGINT', shutdown);  // Catch Ctrl+C
    process.on('SIGTERM', shutdown); // Catch Docker/PM2 stop

  } catch (error) {
    console.error('Failed to initialize server:', error);
    process.exit(1);
  }
};

startServer();