FROM python:3.12-slim

WORKDIR /app

# Copy metadata and sources
COPY pyproject.toml /app/pyproject.toml
COPY workouts_service /app/workouts_service

# Install deps
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -e .

# Alembic
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini

ENV PYTHONUNBUFFERED=1 \
    PORT=8004

EXPOSE 8004

CMD alembic upgrade head && \
    uvicorn workouts_service.main:app --host 0.0.0.0 --port ${PORT}
