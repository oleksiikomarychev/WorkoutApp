FROM python:3.12-slim

WORKDIR /app

# Install system dependencies if needed (none for now)

# Copy project metadata and sources
COPY ./pyproject.toml /app/pyproject.toml
COPY ./user_max_service /app/user_max_service

# Install dependencies (editable install)
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -e .

# Copy alembic config and migrations
COPY ./alembic /app/alembic
COPY ./alembic.ini /app/alembic.ini
COPY ./run_migrations.sh /app/run_migrations.sh

ENV PYTHONUNBUFFERED=1 \
    PORT=8003

EXPOSE 8003

# Run migrations then start service
# CMD alembic upgrade head && \
CMD ["sh", "-c", "echo 'Starting user-max-service on port 8003' && uvicorn user_max_service.main:app --host 0.0.0.0 --port ${PORT}"]
