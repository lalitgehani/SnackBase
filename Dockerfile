# Stage 1: Build React frontend
FROM node:22-alpine AS frontend-builder

WORKDIR /app/ui

# Copy package files for layer caching
COPY ui/package.json ui/package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy source files and build
COPY ui/ .
RUN npm run build

# Stage 2: Python backend with embedded frontend
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# Sync dependencies (no dev deps)
RUN uv sync --frozen --no-dev

# Copy built frontend from stage 1 into ./static
COPY --from=frontend-builder /app/ui/dist ./static

# Expose default port
EXPOSE 8000

# Run the application
CMD ["sh", "-c", "uv run uvicorn snackbase.infrastructure.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
