import dotenv from 'dotenv';
dotenv.config();

export const JWT_SECRET = process.env.JWT_SECRET;
if (!JWT_SECRET) {
  throw new Error('FATAL ERROR: JWT_SECRET is not defined in environment variables.');
}

// Issue #83: ML Internal Shared Secret
export const ML_INTERNAL_TOKEN = process.env.ML_INTERNAL_TOKEN || 'dev-secret-internal-token-change-in-production';

if (process.env.NODE_ENV === 'production' && (!process.env.ML_INTERNAL_TOKEN || process.env.ML_INTERNAL_TOKEN === 'dev-secret-internal-token-change-in-production')) {
  throw new Error('FATAL ERROR: ML_INTERNAL_TOKEN must be configured in production environment.');
}
