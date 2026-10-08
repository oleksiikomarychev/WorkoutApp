# ===== BUILD STAGE =====
FROM python:3.12-slim AS builder

# Build environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
RUN pip install --upgrade pip && pip install uv

# Copy backend-common and plans-service
RUN mkdir -p /app/libs
COPY libs/backend-common /app/libs/backend-common
COPY services/plans-service /app

# Install dependencies without workspace resolution
# Modify pyproject.toml to use path dependency instead of workspace
RUN sed -i 's/backend-common = { workspace = true }/backend-common = { path = "\/app\/libs\/backend-common" }/' pyproject.toml
RUN uv sync

# ===== RUNTIME STAGE =====
FROM python:3.12-slim AS runtime

# Runtime environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_NO_DEV=1 \
    PATH="/app/.venv/bin:$PATH" \
    HOST=0.0.0.0 \
    PORT=8005

# Install runtime system dependencies (PostgreSQL client needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed virtual environment
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app /app

# Create data directory
RUN mkdir -p /app/data

# Copy supervisord configuration
COPY services/plans-service/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create log directories for supervisord
RUN mkdir -p /var/log/supervisor

EXPOSE 8005 50053

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]