import dotenv from 'dotenv';
dotenv.config();

export const JWT_SECRET = process.env.JWT_SECRET;
if (!JWT_SECRET) {
  throw new Error('FATAL ERROR: JWT_SECRET is not defined in environment variables.');
}

// Issue #83: ML Internal Shared Secret (CWE-1392: require explicit development mode)
const currentEnv = (process.env.NODE_ENV || process.env.ENV || '').toLowerCase();
const isExplicitDevOrTest = ['development', 'dev', 'local', 'test'].includes(currentEnv);

export const ML_INTERNAL_TOKEN = process.env.ML_INTERNAL_TOKEN || (
  isExplicitDevOrTest ? 'dev-secret-internal-token-change-in-production' : null
);

if (!ML_INTERNAL_TOKEN || (!isExplicitDevOrTest && ML_INTERNAL_TOKEN === 'dev-secret-internal-token-change-in-production')) {
  throw new Error('FATAL ERROR: ML_INTERNAL_TOKEN must be explicitly configured when not running in development mode.');
}

if (typeof ML_INTERNAL_TOKEN === 'string' && /[^\x00-\x7F]/.test(ML_INTERNAL_TOKEN)) {
  throw new Error('FATAL ERROR: ML_INTERNAL_TOKEN must contain only ASCII characters.');
}
