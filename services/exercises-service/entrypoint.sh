#!/bin/sh
set -e

# Run migrations
cd /app/services/exercises-service
alembic upgrade head

# Start the application
exec "$@"
