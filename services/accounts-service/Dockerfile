FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8007

ENV UV_NO_DEV=1 \
    PATH="/app/.venv/bin:$PATH"

# Install dependencies via uv (workspace lock)
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir uv

COPY . /app

RUN uv sync --frozen --all-packages

# Install supervisord
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Alembic config and migrations
COPY services/accounts-service/alembic.ini /app/alembic.ini
COPY services/accounts-service/alembic /app/alembic
RUN mkdir -p /app/alembic/versions

# Copy supervisord configuration
COPY services/accounts-service/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create log directories for supervisord
RUN mkdir -p /var/log/supervisor

EXPOSE 8007 50055

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
