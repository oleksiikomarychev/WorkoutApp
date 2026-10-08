# ===== BUILD STAGE =====
FROM python:3.12-slim AS builder

# Build environment
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Install build dependencies (включая ML зависимости)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
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

# Copy source code first for editable install
COPY . .

# Install dependencies
RUN uv sync --all-packages

# ===== RUNTIME STAGE =====
FROM python:3.12-slim AS runtime

# Runtime environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_DEV=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy installed virtual environment
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app /app

EXPOSE 8006

CMD ["sh", "-c", "LOWER_LOG_LEVEL=$(printf '%s' \"${LOG_LEVEL:-info}\" | tr '[:upper:]' '[:lower:]'); uvicorn agent_service.main:app --host 0.0.0.0 --port ${PORT:-8006} --log-level ${LOWER_LOG_LEVEL}"]