# Test Database Setup

This document explains how to set up the test database for running persistence tests.

## Prerequisites

- PostgreSQL installed and running
- Database `infysight_users` created
- User `infysight_dbadmin` with password `infysight_dbadmin123` created with full privileges

## One-Time Setup

Run these commands once before running persistence tests:

```bash
# 1. Run migrations to create schema
alembic upgrade head

# 2. Seed the database with test data
python scripts/seed_infysight.py
```

## Configuration

### Database Selection

The test suite supports **multiple databases** via the `DATABASE_URL` environment variable:

**SQLite (default - no setup required):**
```bash
export DATABASE_URL="sqlite+aiosqlite:///./test_infysight.db"
```

**PostgreSQL (production parity):**
```bash
export DATABASE_URL="postgresql+asyncpg://infysight_dbadmin:infysight_dbadmin123@localhost/infysight_users"
```

**MySQL (future support):**
```bash
export DATABASE_URL="mysql+aiomysql://user:pass@localhost/infysight_db"
```

### Centralized Configuration

Database configuration is managed in `tests/persistence/conftest.py`:

```python
from adapters.persistence.db_config import DatabaseConfig, get_database_url

# Constitution Section IV compliance: SQLite default for local dev
DATABASE_URL = get_database_url(
    default="sqlite+aiosqlite:///./test_infysight.db"
)

# Auto-detects database dialect and configures appropriately
DB_CONFIG = DatabaseConfig.from_url(DATABASE_URL)
```

## Test Isolation

Tests use transaction rollback for isolation:
- Each test runs in its own transaction
- Changes are rolled back after each test
- Schema must exist before tests run
- Tests do NOT create/drop tables (except migration smoke tests)

## VS Code Test UI

If the VS Code test UI shows tests as failed:
1. Ensure migrations have been run: `alembic upgrade head`
2. Ensure database is seeded: `python scripts/seed_infysight.py`
3. Refresh the test view in VS Code
4. Re-run the tests

## Troubleshooting

**Error: `relation "table_name" does not exist`**
- Run migrations: `alembic upgrade head`

**Error: `password authentication failed`**
- Check database credentials in conftest.py
- Ensure PostgreSQL user exists with correct password

**Tests pass in terminal but fail in VS Code**
- VS Code may be caching old test results
- Refresh the test view
- Restart VS Code if needed
