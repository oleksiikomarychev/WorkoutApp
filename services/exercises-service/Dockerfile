FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy project first to leverage Docker layer cache
COPY pyproject.toml /app/
COPY exercises_service /app/exercises_service
COPY alembic.ini /app/
COPY alembic /app/alembic
COPY entrypoint.sh /app/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir . \
    && chmod +x /app/entrypoint.sh

# Ensure sqlite data dir exists for default mode
RUN mkdir -p /app/data
VOLUME ["/app/data"]

ENV DB_PATH=/app/data/exercises.db
ENV EXERCISES_DATABASE_URL=sqlite+aiosqlite:////app/data/exercises.db

EXPOSE 8002

CMD ["/app/entrypoint.sh", "sh", "-c", "uvicorn exercises_service.main:app --host 0.0.0.0 --port ${PORT:-8002} --log-level ${LOG_LEVEL:-info}"]
