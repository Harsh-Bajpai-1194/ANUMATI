FROM node:20-alpine

WORKDIR /app

# Copy dependency manifests
COPY package*.json ./

# Install dependencies (including Prisma CLI for generation)
RUN npm ci

# Copy Prisma schema and run code generation
COPY prisma ./prisma/
ENV DATABASE_URL="postgresql://dummy:dummy@localhost:5432/dummy"
RUN npx prisma generate

# Copy the rest of the backend source code
COPY . .

# Ensure upload directory exists with least-privilege permissions (755)
RUN mkdir -p uploads && chmod 755 uploads

EXPOSE 5000

# Health check for Express backend
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:5000/ || exit 1

# Automatically apply pending migrations before launching server
CMD ["sh", "-c", "npx prisma migrate deploy && exec node src/server.js"]