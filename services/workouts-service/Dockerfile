FROM python:3.12-slim

WORKDIR /app

# Install deps
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir uv

ENV UV_NO_DEV=1 \
    PATH="/app/.venv/bin:$PATH"

COPY . /app

RUN uv sync --all-packages

# Install supervisord
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Alembic
COPY services/workouts-service/alembic /app/alembic
COPY services/workouts-service/alembic.ini /app/alembic.ini
COPY services/workouts-service/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copy supervisord configuration
COPY services/workouts-service/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create log directories for supervisord
RUN mkdir -p /var/log/supervisor

ENV PYTHONUNBUFFERED=1 \
    PORT=8004

EXPOSE 8004 50054

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
