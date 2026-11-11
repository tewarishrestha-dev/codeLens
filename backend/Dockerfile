# CodeLens backend — production image.
# Build context must be the repository root so `backend.app.*` imports work:
#   docker build -f backend/Dockerfile -t codelens-backend .
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies first for better layer caching.
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Application code only (no tests, caches, or local data — see .dockerignore).
COPY backend/ /app/backend/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CODELENS_DATA_DIR=/data/codelens

RUN mkdir -p /data/codelens

EXPOSE 8000

# No --reload in production. Bind all interfaces so the container is reachable.
# Uses ${PORT:-8000} to automatically support Render, Railway, and local containers.
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
