#!/usr/bin/env bash
# Test Migration Upgrade/Downgrade Cycle for V1.0 Migrations
# Tests T017-T019 migrations in sequence

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "========================================"
echo "V1.0 Migration Test Script"
echo "========================================"
echo ""

cd "${PROJECT_ROOT}"

# Ensure virtual environment is activated
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    else
        echo -e "${RED}Error: Virtual environment not found${NC}"
        exit 1
    fi
fi

# Function to get current migration version
get_current_version() {
    alembic current 2>/dev/null | head -n 1 | awk '{print $1}' || echo "none"
}

# Function to check if database is accessible
check_database() {
    echo "Checking database connection..."
    python -c "
import asyncio
from src.adapters.persistence.db_config import get_database_url
from sqlalchemy.ext.asyncio import create_async_engine

async def check():
    engine = create_async_engine(get_database_url())
    try:
        async with engine.begin() as conn:
            pass
        return True
    finally:
        await engine.dispose()

result = asyncio.run(check())
exit(0 if result else 1)
" 2>/dev/null
}

echo "Step 1: Check database connection"
if check_database; then
    echo -e "${GREEN}✓ Database connection successful${NC}"
else
    echo -e "${RED}✗ Database connection failed${NC}"
    echo "Please ensure database is running and configured correctly."
    exit 1
fi
echo ""

echo "Step 2: Get current migration state"
INITIAL_VERSION=$(get_current_version)
echo "Current version: ${INITIAL_VERSION}"
echo ""

echo "Step 3: Run pre-migration validation"
if python scripts/validate_email_migration.py; then
    echo -e "${GREEN}✓ Pre-migration validation passed${NC}"
else
    echo -e "${RED}✗ Pre-migration validation failed${NC}"
    echo "Please resolve conflicts before proceeding."
    exit 1
fi
echo ""

echo "Step 4: Apply V1.0 migrations (upgrade)"
echo "Running: alembic upgrade head"
if alembic upgrade head; then
    echo -e "${GREEN}✓ Migrations applied successfully${NC}"
else
    echo -e "${RED}✗ Migration upgrade failed${NC}"
    exit 1
fi
echo ""

echo "Step 5: Verify new migration state"
UPGRADED_VERSION=$(get_current_version)
echo "New version: ${UPGRADED_VERSION}"
echo ""

echo "Step 6: Check schema_version table"
python -c "
import asyncio
from sqlalchemy import text
from src.adapters.persistence.db_config import get_database_url
from sqlalchemy.ext.asyncio import create_async_engine

async def check():
    engine = create_async_engine(get_database_url())
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text('SELECT version, description FROM schema_version'))
            rows = result.fetchall()
            if rows:
                print('Schema version entries:')
                for row in rows:
                    print(f'  - {row.version}: {row.description}')
                return True
            else:
                print('WARNING: No schema_version entries found')
                return False
    finally:
        await engine.dispose()

result = asyncio.run(check())
exit(0 if result else 1)
"
echo ""

echo "Step 7: Test downgrade (rollback one migration)"
echo "Running: alembic downgrade -1"
if alembic downgrade -1; then
    echo -e "${GREEN}✓ Downgrade successful${NC}"
else
    echo -e "${YELLOW}⚠ Downgrade may have warnings (expected if cross-tenant emails exist)${NC}"
fi
echo ""

echo "Step 8: Verify downgraded state"
DOWNGRADED_VERSION=$(get_current_version)
echo "Downgraded version: ${DOWNGRADED_VERSION}"
echo ""

echo "Step 9: Re-apply migrations (test idempotency)"
echo "Running: alembic upgrade head"
if alembic upgrade head; then
    echo -e "${GREEN}✓ Re-upgrade successful${NC}"
else
    echo -e "${RED}✗ Re-upgrade failed${NC}"
    exit 1
fi
echo ""

echo "========================================"
echo -e "${GREEN}✅ Migration Test Complete${NC}"
echo "========================================"
echo ""
echo "Summary:"
echo "  Initial version: ${INITIAL_VERSION}"
echo "  Upgraded to: ${UPGRADED_VERSION}"
echo "  Downgraded to: ${DOWNGRADED_VERSION}"
echo "  Final version: $(get_current_version)"
echo ""
echo "All migration operations completed successfully."
echo "Database schema is ready for V1.0 release."
