FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy project metadata and shared backend-common library
COPY services/exercises-service/pyproject.toml /app/pyproject.toml
COPY libs/backend-common /libs/backend-common

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --only main --no-root

# Copy application code and entrypoint
COPY services/exercises-service/exercises_service /app/exercises_service
COPY services/exercises-service/alembic.ini /app/
COPY services/exercises-service/alembic /app/alembic
COPY services/exercises-service/entrypoint.sh /app/

RUN chmod +x /app/entrypoint.sh

# Ensure sqlite data dir exists for default mode
RUN mkdir -p /app/data
VOLUME ["/app/data"]

ENV DB_PATH=/app/data/exercises.db
ENV EXERCISES_DATABASE_URL=sqlite+aiosqlite:////app/data/exercises.db

EXPOSE 8002

CMD ["/app/entrypoint.sh", "sh", "-c", "LOWER_LOG_LEVEL=$(printf '%s' \"${LOG_LEVEL:-info}\" | tr '[:upper:]' '[:lower:]'); uvicorn exercises_service.main:app --host 0.0.0.0 --port ${PORT:-8002} --log-level ${LOWER_LOG_LEVEL}"]
