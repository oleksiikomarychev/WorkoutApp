FROM python:3.12-slim

WORKDIR /app

# Install deps
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir uv

ENV UV_NO_DEV=1 \
    PATH="/app/.venv/bin:$PATH"

COPY services/rpe-service /app
COPY services/rpe-service/pyproject.toml /app/pyproject.toml

RUN uv sync --all-packages

# Install supervisord
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy supervisord configuration
COPY services/rpe-service/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create log directories for supervisord
RUN mkdir -p /var/log/supervisor

ENV PYTHONUNBUFFERED=1 \
    RPE_TABLE_PATH=/app/rpe_table.json

EXPOSE 8001 50051

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
