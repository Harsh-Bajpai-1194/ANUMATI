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

# Ensure upload directory exists and has appropriate permissions
RUN mkdir -p uploads && chmod 777 uploads

EXPOSE 5000

# Health check for Express backend
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:5000/ || exit 1

CMD ["node", "src/server.js"]