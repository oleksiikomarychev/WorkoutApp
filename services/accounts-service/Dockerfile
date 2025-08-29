FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml /app/
COPY accounts_service /app/accounts_service

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

EXPOSE 8006

CMD ["uvicorn", "accounts_service.main:app", "--host", "0.0.0.0", "--port", "8006"]
