#!/bin/bash
set -e

# Install dependencies
pip install -e .

# Run migrations
alembic upgrade heads

# Start the service
uvicorn user_max_service.main:app --host 0.0.0.0 --port 8003
