FROM python:3.12-slim

WORKDIR /app

# Copy metadata and sources
COPY services/workouts-service/pyproject.toml /app/pyproject.toml
COPY services/workouts-service/workouts_service /app/workouts_service
COPY libs/backend-common /libs/backend-common

# Install deps
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -e .

# Alembic
COPY services/workouts-service/alembic /app/alembic
COPY services/workouts-service/alembic.ini /app/alembic.ini
COPY services/workouts-service/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV PYTHONUNBUFFERED=1 \
    PORT=8004

EXPOSE 8004

CMD ["/app/entrypoint.sh"]
