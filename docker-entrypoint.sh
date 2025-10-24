#!/bin/sh
# Docker entrypoint script for GitHubSpecKit FastAPI application
# Handles database migrations and application startup

set -e

echo "🚀 Starting GitHubSpecKit API..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
until pg_isready -h postgres -U postgres; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done
echo "✅ PostgreSQL is ready!"

# Wait for Redis to be ready
echo "⏳ Waiting for Redis..."
until redis-cli -h redis ping | grep -q PONG; do
  echo "Redis is unavailable - sleeping"
  sleep 2
done
echo "✅ Redis is ready!"

# Run database migrations
echo "🔄 Running database migrations..."
alembic upgrade head
echo "✅ Migrations complete!"

# Optional: Seed database with initial data (if SEED_DATABASE env var is set)
if [ "$SEED_DATABASE" = "true" ]; then
  echo "🌱 Seeding database..."
  python -m cli.db_bootstrap \
    --tenant-slug="${SEED_TENANT_SLUG:-primary}" \
    --admin-email="${SEED_ADMIN_EMAIL:-admin@example.com}"
  echo "✅ Database seeded!"
fi

# Start the FastAPI application
echo "🎯 Starting FastAPI server on 0.0.0.0:8000..."
exec uvicorn adapters.api.app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --log-level info \
  --access-log
