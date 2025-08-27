FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml /app/
COPY plans_service /app/plans_service
RUN pip install --upgrade pip && pip install -e .
COPY alembic.ini /app/
COPY alembic /app/alembic

ENV HOST=0.0.0.0 PORT=8005

RUN mkdir -p /app/data

CMD alembic upgrade head && uvicorn plans_service.main:app --host $HOST --port $PORT
