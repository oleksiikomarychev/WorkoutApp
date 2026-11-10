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
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir uv

# Copy the CRM service's dependency manifest
COPY services/crm-service/pyproject.toml ./pyproject.toml

# Copy workspace dependency
RUN mkdir -p /app/libs
COPY libs/backend-common /app/libs/backend-common

# Copy source code first for editable install
COPY services/crm-service/crm_service ./crm_service
COPY services/crm-service/alembic ./alembic
COPY services/crm-service/alembic.ini ./alembic.ini

# Install dependencies
RUN python -m venv .venv && \
    .venv/bin/pip install --no-cache-dir -e /app/libs/backend-common && \
    .venv/bin/pip install --no-cache-dir -e .

# ===== RUNTIME STAGE =====
FROM python:3.12-slim AS runtime

# Runtime environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8008 \
    UV_NO_DEV=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy installed virtual environment
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app /app

EXPOSE 8008

CMD ["uvicorn", "crm_service.main:app", "--host", "0.0.0.0", "--port", "8008"]
