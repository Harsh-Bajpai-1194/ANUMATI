# Stage 1: Build the Webpack production bundle
FROM node:24-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Serve through Nginx
FROM nginx:alpine

# Copy custom Nginx configuration for React Router support
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy bundled assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]