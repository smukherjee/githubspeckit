# Database Testing Guide (Phase 3)

## Overview

Phase 3 introduces database integration tests marked with `@pytest.mark.db`. These tests are **excluded from the default fast test suite** to maintain rapid feedback loops.

## Prerequisites

1. **PostgreSQL 14+** running locally or accessible via network
2. **Test database** created with appropriate permissions

## Quick Setup

### Using Docker (Recommended)

```bash
# Start PostgreSQL in Docker
docker run -d \
  --name githubspeckit-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=githubspeckit_test \
  -p 5432:5432 \
  postgres:16-alpine

# Verify container is running
docker ps | grep githubspeckit-postgres
```

### Using Local PostgreSQL

```bash
# Create test database
./scripts/setup_test_db.sh

# Or manually:
createdb githubspeckit_test
```

## Running Database Tests

### Environment Configuration

Set the test database URL (default shown):

```bash
export TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/githubspeckit_test"
```

### Run DB Tests Only

```bash
# All database tests
pytest -v -m db

# Specific test file
pytest tests/persistence/test_migration_smoke.py -v -m db

# Single test
pytest tests/persistence/test_migration_smoke.py::TestMigrationSmoke::test_fresh_migration_applies_successfully -v -m db
```

### Run Fast Suite (Excludes DB Tests)

```bash
# Default pytest run (excludes @pytest.mark.db)
pytest -v -m "not db"

# Or use the default (no marker filter needed once configured)
pytest -v
```

## TEST-DB-04: Migration Smoke Tests

**Purpose**: Validate Alembic migration integrity and idempotency (FR-015, FR-052)

**Tests**:
1. `test_fresh_migration_applies_successfully` - Initial migration applies without error
2. `test_migration_idempotency` - Repeat application succeeds (no-op)
3. `test_expected_tables_exist` - All 11 tables created
4. `test_expected_indexes_exist` - Key indexes present
5. `test_expected_foreign_keys_exist` - FK constraints correct (CASCADE/SET NULL)
6. `test_expected_enums_exist` - 5 PostgreSQL enum types created
7. `test_downgrade_and_reupgrade` - Bidirectional migration integrity

**Expected Duration**: ~2-5 seconds per test (depending on DB I/O)

## Troubleshooting

### Connection Refused

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Or for Docker
docker ps | grep postgres
```

### Permission Denied

Ensure the database user has CREATE/DROP privileges:

```sql
GRANT ALL PRIVILEGES ON DATABASE githubspeckit_test TO postgres;
```

### Migration Already Applied

Tests use `clean_db` fixture to reset state. If you see stale schema:

```bash
# Drop and recreate test database
dropdb githubspeckit_test
createdb githubspeckit_test
```

## CI/CD Integration

For CI pipelines, use PostgreSQL service containers:

### GitHub Actions Example

```yaml
services:
  postgres:
    image: postgres:16-alpine
    env:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: githubspeckit_test
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
    ports:
      - 5432:5432

steps:
  - name: Run DB Tests
    env:
      TEST_DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/githubspeckit_test
    run: pytest -v -m db
```

## Performance Considerations

- **Fast suite** (in-memory): ~1-5 seconds total
- **DB suite**: ~10-30 seconds (depends on test count)
- **Full suite**: Fast + DB combined

Recommendation: Run fast suite during development, DB suite pre-commit or in CI.

## Phase 3 Roadmap

- ✅ **TEST-DB-01**: Repository parity tests (in-memory baseline validation)
- ✅ **IMPL-DB-02**: SQLAlchemy models (11 entities)
- ✅ **IMPL-DB-03**: Alembic configuration + initial migration
- 🔄 **TEST-DB-04**: Migration smoke tests (current)
- ⏳ **IMPL-DB-05**: Persistence adapters (SQLAlchemy repository implementations)
- ⏳ **TEST-DB-06+**: Seed idempotency, isolation, metrics, replay, coverage...

---

For questions or issues, see `specs/001-modern-enterprise-grade/tasks.md` Phase 3 section.
