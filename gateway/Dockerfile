# ===== BUILD STAGE =====
FROM python:3.12-slim AS builder

# Build environment
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir uv

# Copy entire workspace for backend-common dependency
COPY libs/backend-common /app/libs/backend-common
COPY gateway/pyproject.toml /app/gateway/
COPY gateway/gateway_app /app/gateway/gateway_app
COPY gateway/proto_gen /app/gateway/proto_gen

WORKDIR /app/gateway

# Create virtual environment and install dependencies
RUN uv venv .venv \
    && uv pip install --no-cache-dir -e /app/libs/backend-common \
    && uv pip install --no-cache-dir -e .

# ===== RUNTIME STAGE =====
FROM python:3.12-slim AS runtime

# Runtime environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install runtime system dependencies (ca-certificates needed)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy installed virtual environment
COPY --from=builder /app/gateway/.venv /app/.venv

# Copy application code
COPY --from=builder /app/gateway /app

# Copy libs for editable dependencies
COPY --from=builder /app/libs /app/libs

EXPOSE 8000

CMD ["sh", "-c", "LOWER_LOG_LEVEL=$(printf '%s' \"${LOG_LEVEL:-info}\" | tr '[:upper:]' '[:lower:]'); python -m uvicorn gateway_app.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level ${LOWER_LOG_LEVEL}"]
