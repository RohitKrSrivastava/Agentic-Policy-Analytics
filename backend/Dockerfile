# ==============================================================================
# Unified Production Multi-Stage Dockerfile for GovPolicy AI Platform
# Stage 1: Build React/Vite Frontend
# Stage 2: Install Python dependencies
# Stage 3: Assemble lightweight, secure, non-root runtime container
# ==============================================================================

# --- Stage 1: Build Frontend ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# --- Stage 2: Python Dependencies ---
FROM python:3.11-slim AS python-builder
WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Stage 3: Final Production Runtime ---
FROM python:3.11-slim AS runtime
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy installed Python packages
COPY --from=python-builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV ENVIRONMENT=production
ENV DEBUG=false

# Copy compiled frontend SPA
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Copy backend application and datasets
COPY backend /app/backend

# Create runtime directories & assign ownership to appuser
RUN mkdir -p /app/backend/data/raw /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/status || exit 1

CMD ["python", "backend/run.py"]
