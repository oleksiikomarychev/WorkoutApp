FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy project first to leverage Docker layer cache
COPY pyproject.toml /app/
COPY coach_service /app/coach_service
COPY alembic.ini /app/
COPY alembic /app/alembic

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Ensure sqlite data dir exists for default mode
RUN mkdir -p /app/data
VOLUME ["/app/data"]

EXPOSE 8007

CMD ["sh", "-c", "alembic upgrade head && uvicorn coach_service.main:app --host 0.0.0.0 --port 8007"]
