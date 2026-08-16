import mongoose from 'mongoose';

let shuttingDown = false;

const connectMongoDB = async () => {
  if (!process.env.MONGODB_URI) {
    throw new Error('FATAL ERROR: MONGODB_URI is not defined in .env');
  }

  try {
    mongoose.connection.on('disconnected', () => {
      if (!shuttingDown) console.warn('MongoDB disconnected unexpectedly! Check your database server.');
    });

    mongoose.connection.on('error', (err) => {
      console.error(`MongoDB runtime error: ${err.message}`);
    });

    const conn = await mongoose.connect(process.env.MONGODB_URI, {
      serverSelectionTimeoutMS: 5000,
    });
    console.log(`MongoDB Connected: ${conn.connection.host}`);
  } catch (error) {
    throw new Error(`Error connecting to MongoDB: ${error.message}`);
  }
};

export default connectMongoDB;

export const getConnection = () => mongoose.connection;

export const disconnectMongoDB = async () => {
  shuttingDown = true;
  if (mongoose.connection.readyState !== 0) {
    await mongoose.connection.close();
  }
};