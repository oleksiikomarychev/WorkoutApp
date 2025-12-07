FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir poetry

COPY gateway/pyproject.toml /app/pyproject.toml
COPY libs/backend-common /libs/backend-common

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --only main --no-root

COPY gateway/gateway_app /app/gateway_app

EXPOSE 8000

CMD ["sh", "-c", "LOWER_LOG_LEVEL=$(printf '%s' \"${LOG_LEVEL:-info}\" | tr '[:upper:]' '[:lower:]'); uvicorn gateway_app.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level ${LOWER_LOG_LEVEL}"]
