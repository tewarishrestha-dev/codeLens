# CodeLens frontend — multi-stage Vite build + Nginx static server.
# Build context is frontend/:
#   docker build -t codelens-frontend frontend/

# ---- Build stage ----
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

# VITE_API_URL is baked in at build time (Vite embeds import.meta.env).
# Default matches the host-mapped backend port from docker-compose.yml.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}

COPY . .
RUN npm run build

# ---- Serve stage ----
FROM nginx:1.27-alpine

# SPA fallback: serve index.html for client-side routes.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
