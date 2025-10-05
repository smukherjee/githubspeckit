#!/usr/bin/env bash
# Setup script for test database (TEST-DB-04 prerequisite)
#
# Creates a PostgreSQL test database for migration smoke tests.
# Usage: ./scripts/setup_test_db.sh

set -euo pipefail

DB_NAME="${TEST_DB_NAME:-githubspeckit_test}"
DB_USER="${TEST_DB_USER:-postgres}"
DB_HOST="${TEST_DB_HOST:-localhost}"
DB_PORT="${TEST_DB_PORT:-5432}"

echo "Setting up test database: $DB_NAME"

# Check if PostgreSQL is running
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; then
    echo "ERROR: PostgreSQL is not running at $DB_HOST:$DB_PORT"
    echo "Please start PostgreSQL or adjust DB_HOST/DB_PORT environment variables."
    exit 1
fi

# Drop database if it exists (clean slate)
echo "Dropping existing test database (if exists)..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "DROP DATABASE IF EXISTS $DB_NAME;" postgres || true

# Create fresh test database
echo "Creating test database..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;" postgres

echo "✅ Test database '$DB_NAME' created successfully"
echo ""
echo "To run migration smoke tests:"
echo "  export TEST_DATABASE_URL=postgresql+asyncpg://$DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo "  pytest tests/persistence/test_migration_smoke.py -v -m db"
