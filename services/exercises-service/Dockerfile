# ===== BUILD STAGE =====
FROM python:3.12-slim AS builder

# Build environment
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir uv

# Copy dependency files (кешируемый слой)
COPY pyproject.toml ./

# Copy workspace dependency
RUN mkdir -p /app/libs
COPY libs/backend-common /app/libs/backend-common
COPY pyproject.toml /app/pyproject.toml

# Install dependencies
RUN uv sync --all-packages

# Copy source code
COPY . .

# Install application
RUN uv sync --all-packages

# Make entrypoint executable
RUN chmod +x /app/services/exercises-service/entrypoint.sh

# ===== RUNTIME STAGE =====
FROM python:3.12-slim AS runtime

# Runtime environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_DEV=1 \
    PATH="/app/.venv/bin:$PATH"

# Install supervisord
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed virtual environment
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app /app

# Create data directory
RUN mkdir -p /app/data/exercise_media

# Copy supervisord configuration
COPY services/exercises-service/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create log directories for supervisord
RUN mkdir -p /var/log/supervisor

EXPOSE 8002 50052

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]