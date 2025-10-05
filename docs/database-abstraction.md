# Database Abstraction Layer

## Overview

This project implements a comprehensive database abstraction layer that complies with **Constitution Section IV**:

> "Swappable implementations: SQLAlchemy (PostgreSQL primary), optional in-memory (tests), SQLite (local dev), and future cloud variants."

The abstraction layer enables seamless switching between database backends without code changes, supporting:

- **PostgreSQL** (production, CI/CD)
- **SQLite** (local development, fast tests)
- **MySQL** (future support ready)

## Architecture

```
src/adapters/persistence/
├── db_config.py          # Database abstraction layer (NEW)
├── models.py             # ORM models with PortableUUID
├── repositories.py       # Repository implementations
└── ...

tests/persistence/
├── conftest.py           # Database-agnostic fixtures
├── test_db_abstraction.py # Abstraction layer tests (NEW)
└── ...
```

### Key Components

1. **DatabaseConfig** (`db_config.py`)
   - Auto-detects dialect from DATABASE_URL
   - Provides dialect-specific engine settings
   - Feature detection (UUID support, JSON, arrays)

2. **PortableUUID** (`db_config.py`)
   - Transparent UUID handling across databases
   - PostgreSQL: Native UUID type
   - SQLite/MySQL: CHAR(36) with automatic conversion

3. **Database-Agnostic Fixtures** (`conftest.py`)
   - Auto-detects database from environment
   - SQLite: Enables foreign key enforcement (PRAGMA)
   - Transaction rollback for test isolation

## Usage

### Setting Database Backend

Control which database to use via the `DATABASE_URL` environment variable:

```bash
# PostgreSQL (production default)
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/infysight_users"

# SQLite (local development default)
export DATABASE_URL="sqlite+aiosqlite:///./infysight_dev.db"

# MySQL (future support)
export DATABASE_URL="mysql+aiomysql://user:pass@localhost/infysight_db"
```

### Running Tests

**With PostgreSQL (requires PostgreSQL server):**
```bash
export DATABASE_URL="postgresql+asyncpg://infysight_dbadmin:infysight_dbadmin123@localhost/infysight_users"
alembic upgrade head
pytest tests/persistence/
```

**With SQLite (no external dependencies):**
```bash
# Method 1: Explicit URL
export DATABASE_URL="sqlite+aiosqlite:///./test_infysight.db"
alembic upgrade head
pytest tests/persistence/

# Method 2: Let conftest.py use default SQLite
unset DATABASE_URL
pytest tests/persistence/  # Uses sqlite+aiosqlite:///./test_infysight.db
```

### Development Workflow

**Quick Start (SQLite - fastest):**
```bash
# No PostgreSQL required!
cd /path/to/project
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Setup database
export DATABASE_URL="sqlite+aiosqlite:///./dev.db"
alembic upgrade head

# Run tests (sub-second!)
pytest tests/persistence/test_repository_parity.py
# ======================== 24 passed in 0.13s ========================
```

**Full Integration (PostgreSQL):**
```bash
# Requires PostgreSQL server running
export DATABASE_URL="postgresql+asyncpg://infysight_dbadmin:infysight_dbadmin123@localhost/infysight_users"
alembic upgrade head
pytest tests/persistence/
```

## Migrations

Alembic migrations work seamlessly across databases:

```bash
# Generate migration (auto-detects database)
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head  # Uses DATABASE_URL

# With SQLite
DATABASE_URL="sqlite+aiosqlite:///./dev.db" alembic upgrade head

# With PostgreSQL
DATABASE_URL="postgresql+asyncpg://localhost/mydb" alembic upgrade head
```

### SQLite-Specific Handling

The migration system automatically handles SQLite limitations:

- **Batch mode**: Enabled for SQLite (ALTER TABLE workarounds)
- **Foreign keys**: Automatically enabled via PRAGMA
- **UUIDs**: Transparently converted to CHAR(36)

## Feature Detection

The abstraction layer provides dialect-specific feature detection:

```python
from adapters.persistence.db_config import get_db_config

config = get_db_config()

if config.is_postgres:
    # Use PostgreSQL-specific features
    pass
elif config.is_sqlite:
    # Handle SQLite limitations
    pass

# Or check specific features
if config.supports_uuid:
    # Use native UUID type
    pass
else:
    # Use string-based UUID (automatic)
    pass
```

## Performance Comparison

**Test Suite Performance (24 repository parity tests):**

| Database   | Time    | Setup Required |
|------------|---------|----------------|
| SQLite     | 0.13s   | None          |
| PostgreSQL | 1.5s    | Server running |

**Recommendation:**
- Local development: SQLite (instant setup, fast tests)
- CI/CD: PostgreSQL (production parity)
- Production: PostgreSQL (full features, proven scale)

## Constitution Compliance

✅ **Section IV Requirements Met:**

1. **PostgreSQL (primary)**: Full support with asyncpg driver
2. **SQLite (local dev)**: Full support with aiosqlite driver  
3. **Future cloud variants**: MySQL detection ready, extensible design
4. **Swappable implementations**: Single environment variable switch
5. **No ORM leakage**: Domain models use UUID type, adapter handles conversion

## Troubleshooting

### SQLite Tests Fail with "no such table"

**Problem**: Tables don't exist in SQLite database.

**Solution**:
```bash
DATABASE_URL="sqlite+aiosqlite:///./test_infysight.db" alembic upgrade head
```

### PostgreSQL Connection Refused

**Problem**: PostgreSQL server not running or wrong credentials.

**Solution**:
```bash
# Check server status
pg_isready

# Verify credentials match DATABASE_URL
psql -U infysight_dbadmin -d infysight_users

# Or switch to SQLite for local dev
export DATABASE_URL="sqlite+aiosqlite:///./dev.db"
```

### Foreign Key Violations in SQLite

**Problem**: SQLite foreign key constraints not enforced.

**Solution**: The abstraction layer automatically enables foreign keys via:
```python
# In conftest.py async_session fixture
if DB_CONFIG.is_sqlite:
    await connection.execute(text("PRAGMA foreign_keys=ON"))
```

This is handled automatically - no action needed.

## Adding New Databases

To add support for a new database (e.g., Oracle):

1. **Add dialect to `DatabaseDialect` enum:**
```python
class DatabaseDialect(str, Enum):
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    MYSQL = "mysql"
    ORACLE = "oracle"  # NEW
```

2. **Add detection in `_detect_dialect()`:**
```python
elif base_scheme == 'oracle':
    return DatabaseDialect.ORACLE
```

3. **Add defaults in `_get_dialect_defaults()`:**
```python
elif dialect == DatabaseDialect.ORACLE:
    return {
        "echo": False,
        "pool_size": 5,
        "max_overflow": 10,
    }
```

4. **Update `create_engine()` if needed:**
```python
elif self.dialect == DatabaseDialect.ORACLE:
    kwargs["pool_size"] = self.pool_size
    kwargs["max_overflow"] = self.max_overflow
```

5. **Add driver dependency to `pyproject.toml`:**
```toml
"cx-Oracle>=8.0,<9",  # Oracle driver
```

6. **Add tests in `test_db_abstraction.py`**

That's it! The abstraction layer handles the rest.

## Best Practices

### Local Development
```bash
# Use SQLite for speed
export DATABASE_URL="sqlite+aiosqlite:///./dev.db"
```

### CI/CD
```bash
# Use PostgreSQL for production parity
export DATABASE_URL="postgresql+asyncpg://ci_user:ci_pass@postgres:5432/ci_db"
```

### Testing
```bash
# Fast tests with SQLite
pytest tests/unit/ tests/persistence/

# Full integration with PostgreSQL
DATABASE_URL="postgresql+..." pytest tests/
```

### Production
```bash
# Always PostgreSQL in production
export DATABASE_URL="postgresql+asyncpg://prod_user:${SECRET_PASS}@db.example.com/prod_db"
```

## References

- Constitution: `.specify/memory/constitution.md` (Section IV)
- Database Config: `src/adapters/persistence/db_config.py`
- Test Fixtures: `tests/persistence/conftest.py`
- Abstraction Tests: `tests/persistence/test_db_abstraction.py`
