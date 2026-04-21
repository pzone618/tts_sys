# Multi-stage build for TTS System
FROM python:3.13-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml .python-version ./
COPY packages/ packages/

# Install dependencies
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.13-slim

WORKDIR /app

# Copy uv and virtual environment from builder
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/packages /app/packages

# Copy additional files
COPY migrations/ migrations/
COPY alembic.ini ./
COPY .env.example .env

# Create storage and database directories
RUN mkdir -p storage/cache storage/temp database

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"

# Expose port (configurable via API_PORT env var)
ARG API_PORT=8000
EXPOSE ${API_PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.getenv(\"API_PORT\", \"8000\")}/api/v1/health')"

# Run migrations and start server
CMD sh -c "alembic upgrade head && uvicorn packages.api.main:app --host 0.0.0.0 --port ${API_PORT:-8000}"
