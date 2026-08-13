import 'dotenv/config';
import prisma from '../src/config/db.js';

async function main() {
  try {
    // Try a simple query to test connection
    const userCount = await prisma.user.count();
    console.log(`Database connection successful! Current user count: ${userCount}`);
  } catch (error) {
    console.error(
      `Database connection failed: ${error.message}${error.code ? ` (code: ${error.code})` : ''}`
    );
    process.exitCode = 1;
  } finally {
    await prisma.$disconnect();
  }
}

main();
