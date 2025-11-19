FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

#Копируем проект в Docker-контейнер для оптимизации кэширования слоев
COPY pyproject.toml /app/
COPY rpe_service /app/rpe_service
COPY rpe_table.json /app/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

EXPOSE 8001

CMD ["sh", "-c", "uvicorn rpe_service.main:app --host 0.0.0.0 --port ${PORT:-8001} --log-level ${LOG_LEVEL:-info}"]
