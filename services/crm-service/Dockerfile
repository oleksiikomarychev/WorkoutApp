FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8008

# Copy project metadata and shared backend-common library
COPY services/crm-service/pyproject.toml /app/pyproject.toml
COPY libs/backend-common /libs/backend-common

# Install dependencies via Poetry
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main --no-root

# Copy application sources and Alembic config
COPY services/crm-service/crm_service /app/crm_service
COPY services/crm-service/alembic.ini /app/alembic.ini
COPY services/crm-service/alembic /app/alembic
RUN mkdir -p /app/alembic/versions

EXPOSE 8008

CMD ["uvicorn", "crm_service.main:app", "--host", "0.0.0.0", "--port", "8008"]
