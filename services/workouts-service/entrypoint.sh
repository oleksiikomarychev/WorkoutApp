#!/bin/sh
set -e
alembic upgrade head
exec uvicorn workouts_service.main:app --host 0.0.0.0 --port "${PORT:-8004}"
