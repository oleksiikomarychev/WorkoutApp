FROM python:3.12-slim

WORKDIR /app

# Install system dependencies if needed (none for now)

# Copy project metadata and sources
COPY services/user-max-service/pyproject.toml /app/pyproject.toml
COPY services/user-max-service/user_max_service /app/user_max_service
COPY libs/backend-common /libs/backend-common

# Install dependencies (editable install)
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -e .

# Copy alembic config and migrations
COPY services/user-max-service/alembic /app/alembic
COPY services/user-max-service/alembic.ini /app/alembic.ini

ENV PYTHONUNBUFFERED=1 \
    PORT=8003

EXPOSE 8003

# Run migrations then start service
# CMD alembic upgrade head && \
CMD ["sh", "-c", "echo 'Starting user-max-service on port 8003' && uvicorn user_max_service.main:app --host 0.0.0.0 --port ${PORT}"]
