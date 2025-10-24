"""
IMPL-DB-03: Alembic environment for async SQLAlchemy migrations.

Configures Alembic to work with:
- Async SQLAlchemy 2.x engine
- PostgreSQL via asyncpg driver
- Database URL from environment variable (DATABASE_URL)
- Structured logging for migration lifecycle
- Deterministic naming conventions (FR-015, FR-052)

Usage:
    # Apply all pending migrations
    alembic upgrade head
    
    # Generate new migration
    alembic revision --autogenerate -m "description"
    
    # Check current revision
    alembic current

Dependencies: IMPL-DB-02 (models must exist)
Next: TEST-DB-04 (migration smoke tests)
"""
from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add src directory to Python path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import all models to ensure they're registered with metadata
from src.adapters.persistence.models import Base
from src.adapters.persistence.db_config import DatabaseConfig, get_database_url

# Alembic Config object
config = context.config

# Interpret the config file for Python logging (if present)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata

# Database configuration with abstraction layer
# Constitution Section IV: "Swappable implementations: SQLAlchemy (PostgreSQL primary),
# optional in-memory (tests), SQLite (local dev), and future cloud variants."
#
# V1.0: SQLite support disabled - use PostgreSQL only
#
# Supports:
# - PostgreSQL: postgresql+asyncpg://user:pass@host/db (production)
# - MySQL: mysql+aiomysql://user:pass@host/db (future)
DATABASE_URL = get_database_url(
    default="postgresql+asyncpg://infysight_dbadmin:infysight_dbadmin123@localhost/infysight_users"  # V1.0: Default credentials
)
DB_CONFIG = DatabaseConfig.from_url(DATABASE_URL)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.
    
    Calls to context.execute() here emit the given string to the
    script output.
    """
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Naming convention for constraint generation (deterministic)
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations within a connection context."""
    # V1.0: SQLite support disabled - batch mode not needed
    # render_as_batch = DB_CONFIG.is_sqlite  # Commented out - SQLite disabled
    render_as_batch = False  # PostgreSQL doesn't need batch mode
    
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Naming conventions for constraints (FR-015: deterministic naming)
        render_as_batch=render_as_batch,
        # V1.0: SQLite-specific options removed (SQLite disabled)
        # dialect_opts={"sqlite_synchronous": 0} if DB_CONFIG.is_sqlite else {},
        dialect_opts={},
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode with async engine.
    
    Creates an async engine and associates a connection with the context.
    """
    # Override sqlalchemy.url in alembic.ini
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = DATABASE_URL
    
    # Create async engine
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # No connection pooling for migrations
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (async SQLAlchemy)."""
    asyncio.run(run_async_migrations())


# Determine mode and run
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
