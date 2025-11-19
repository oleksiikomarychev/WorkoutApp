FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8007

# Copy project metadata and sources
COPY pyproject.toml /app/pyproject.toml
COPY accounts_service /app/accounts_service

# Install dependencies (editable install)
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -e .

# Alembic config and migrations
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic
RUN mkdir -p /app/alembic/versions

EXPOSE 8007

CMD ["uvicorn", "accounts_service.main:app", "--host", "0.0.0.0", "--port", "8007"]
