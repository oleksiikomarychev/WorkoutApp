FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for building Python packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (mirrors pyproject.toml)
# Change these lines
RUN pip install --no-cache-dir \
    "fastapi>=0.110.0,<0.112.0" \
    "uvicorn[standard]>=0.29.0,<0.31.0" \
    "httpx==0.28.1" \
    "pydantic>=2.10.0,<2.11.0" \
    "SQLAlchemy>=2.0.29,<2.1.0" \
    "langchain>=0.3.0,<0.4.0" \
    "langchain-community>=0.3.0,<0.4.0" \
    "langchain-google-genai>=0.1.0" \
    "psycopg2-binary>=2.9.7,<2.10.0" \
    "logging>=0.1.0" \
    "alembic>=1.15.0,<2.0.0" \
    "pydantic-ai>=0.0.15,<0.1.0" \
    "google-genai==1.42.0" \
    "json5>=0.9.25,<0.10.0" \
    "huggingface_hub>=0.25.0,<1.0.0" \
    "pillow>=10.0.0,<11.0.0" \
    "google-auth>=2.23.0,<3.0.0" \
    "structlog>=24.0.0,<25.0.0" \
    "asgi-correlation-id>=4.3.1,<5.0.0" \
    "prometheus-fastapi-instrumentator>=6.1.0,<7.0.0" \
    "prometheus-client>=0.16.0,<1.0.0" \
    "sentry-sdk[fastapi]>=2.0.0,<3.0.0" \
    "celery[redis]>=5.4.0,<6.0.0" \
    "redis>=5.0.0,<6.0.0"
# Copy application code
COPY agent_service /app/agent_service
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini


EXPOSE 8006

CMD ["sh", "-c", "LOWER_LOG_LEVEL=$(printf '%s' \"${LOG_LEVEL:-info}\" | tr '[:upper:]' '[:lower:]'); uvicorn agent_service.main:app --host 0.0.0.0 --port ${PORT:-8006} --log-level ${LOWER_LOG_LEVEL}"]