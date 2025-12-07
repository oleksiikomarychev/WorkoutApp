FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies for PostgreSQL client
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

COPY services/plans-service/pyproject.toml /app/pyproject.toml
COPY services/plans-service/plans_service /app/plans_service
COPY libs/backend-common /libs/backend-common
RUN pip install --upgrade pip && pip install -e .
COPY services/plans-service/alembic.ini /app/
COPY services/plans-service/alembic /app/alembic

ENV HOST=0.0.0.0 PORT=8005

RUN mkdir -p /app/data


CMD uvicorn plans_service.main:app --host $HOST --port $PORT
