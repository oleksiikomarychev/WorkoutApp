#!/bin/sh
set -e
exec uvicorn workouts_service.main:app --host 0.0.0.0 --port "${PORT:-8004}"
