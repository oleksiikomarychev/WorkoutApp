FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for building Python packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (mirrors pyproject.toml)
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir poetry

# Copy project metadata and shared backend-common library
COPY services/agent-service/pyproject.toml /app/pyproject.toml
COPY libs/backend-common /libs/backend-common

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --only main --no-root

# Copy application code
COPY services/agent-service/agent_service /app/agent_service
COPY services/agent-service/alembic /app/alembic
COPY services/agent-service/alembic.ini /app/alembic.ini


EXPOSE 8006

CMD ["sh", "-c", "LOWER_LOG_LEVEL=$(printf '%s' \"${LOG_LEVEL:-info}\" | tr '[:upper:]' '[:lower:]'); uvicorn agent_service.main:app --host 0.0.0.0 --port ${PORT:-8006} --log-level ${LOWER_LOG_LEVEL}"]