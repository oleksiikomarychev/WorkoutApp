#!/bin/sh

set -e

# Initialize the database if it doesn't exist
if [ ! -f "$DB_PATH" ]; then
  echo "Initializing database at $DB_PATH"
  touch "$DB_PATH"
fi

# Run migrations
alembic upgrade head

# Start the application
exec "$@"
