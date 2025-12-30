# Multi-stage build for fast builds
FROM python:3.12-slim AS deps

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies (generate lockfile if needed)
# uv sync creates .venv in the current working directory
RUN uv sync --no-dev

# Application stage
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install ffmpeg for pydub (audio conversion)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy virtual environment from deps stage
# uv creates .venv in the working directory (/app/.venv)
COPY --from=deps /app/.venv /app/.venv

# Copy application code
COPY . .

# Use virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Expose port (Railway uses PORT env var)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; import os; port = os.getenv('PORT', '8000'); httpx.get(f'http://localhost:{port}/health')"

# Run application (Railway sets PORT env var)
# Use shell form to properly expand PORT variable
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}

