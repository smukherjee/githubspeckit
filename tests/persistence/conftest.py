"""
Persistence layer test fixtures.

Provides fixtures for:
- In-memory repositories (baseline behavior)
- Database repositories (parity validation)
- Async database session management
- Test database lifecycle

Constitution Section IV: "Swappable implementations: SQLAlchemy (PostgreSQL primary),
optional in-memory (tests), SQLite (local dev), and future cloud variants."

This module implements database-agnostic testing that works with:
- PostgreSQL (default for CI/CD)
- SQLite (local development, fast tests)
- MySQL (future support)

Status: TEST-DB-01 foundation, IMPL-DB-02 session management
"""
from __future__ import annotations

import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import event, text

from adapters.persistence.db_config import DatabaseConfig, get_database_url

# Single source of truth for test database URL
# All persistence tests use this configuration
#
# Constitution compliance: Respects DATABASE_URL env var, falls back to SQLite
# - If DATABASE_URL set: Use that (PostgreSQL for integration tests)
# - If not set: Use SQLite for fast local testing
#
# Examples:
#   - PostgreSQL: export DATABASE_URL="postgresql+asyncpg://infysight_dbadmin:infysight_dbadmin123@localhost/infysight_users"
#   - SQLite: export DATABASE_URL="sqlite+aiosqlite:///./test_infysight.db" (or unset for default)
try:
    # Try to get from settings (respects env var first, then descriptor default)
    from domain.config.settings import get_database_settings
    DATABASE_URL = get_database_settings().database_url
except (ValueError, FileNotFoundError, ImportError):
    # Fallback to SQLite if config not available
    DATABASE_URL = "sqlite+aiosqlite:///./test_infysight.db"

# Create database configuration (auto-detects dialect)
DB_CONFIG = DatabaseConfig.from_url(DATABASE_URL)


@pytest.fixture
def in_memory_tenant_repo():
    """In-memory tenant repository for baseline behavior."""
    from domain.tenants.models import TenantRepository
    return TenantRepository()


@pytest.fixture
def in_memory_user_repo():
    """In-memory user repository for baseline behavior."""
    from domain.users.models import UserRepository
    return UserRepository()


@pytest.fixture
def in_memory_policy_repo():
    """In-memory policy repository for baseline behavior."""
    from domain.policy.models import PolicyRepository
    return PolicyRepository()


@pytest.fixture
def in_memory_featureflag_repo():
    """In-memory feature flag repository for baseline behavior."""
    from domain.featureflags.models import FeatureFlagRepository
    return FeatureFlagRepository()


# Database fixtures (async session management)

@pytest.fixture(scope="session", autouse=True)
def _setup_database_schema():
    """
    Session-scoped fixture to ensure database schema exists.
    
    Runs once before all tests, creates all tables synchronously.
    This avoids event loop conflicts with pytest-asyncio.
    
    Strategy:
    - Module-level: Run migrations via alembic (real-world CI/CD path)
    - For tests: Create tables directly (faster, test-focused)
    """
    import subprocess
    import sys
    
    # Run migrations to create schema
    # This is the same path CI/CD will use, ensuring consistency
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        env={**os.environ, "DATABASE_URL": DATABASE_URL}
    )
    
    if result.returncode != 0:
        pytest.fail(f"Failed to run migrations: {result.stderr}")
    
    yield
    
    # Cleanup handled by individual test rollbacks


@pytest_asyncio.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Database-agnostic async session fixture with transaction rollback.
    
    Features:
    - Works with PostgreSQL, SQLite, and MySQL (future)
    - Auto-detects dialect from DATABASE_URL
    - SQLite: Enables foreign key enforcement
    - Each test gets fresh session with automatic rollback for isolation
    - Function-scoped: New session per test
    
    Constitution compliance: Implements swappable database backends per Section IV.
    
    Test Isolation Strategy:
    - Schema created once at session start (_setup_database_schema)
    - Each test creates its own engine and connection
    - Transaction rolls back after test (data isolation)
    - Tables remain for next test (performance)
    
    SQLite vs PostgreSQL Transaction Handling:
    - SQLite: Uses autobegin, explicit begin() causes errors
    - PostgreSQL: Supports explicit nested transactions with savepoints
    """
    # Create engine for this test
    engine = DB_CONFIG.create_engine()
    
    try:
        # Create connection for this test
        async with engine.connect() as connection:
            # SQLite-specific: Enable foreign key constraints per connection
            # (SQLite disables them by default, breaking referential integrity)
            if DB_CONFIG.is_sqlite:
                await connection.execute(text("PRAGMA foreign_keys=ON"))
            
            # Create session bound to this connection
            # SQLite: Uses connection's autobegin transaction
            # PostgreSQL: Can use explicit transaction + savepoints
            async_session_maker = async_sessionmaker(
                bind=connection,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            async with async_session_maker() as session:
                try:
                    yield session
                finally:
                    # Rollback any changes made during the test
                    await session.rollback()
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_session) -> AsyncSession:
    """Alias for async_session for backward compatibility."""
    return async_session


@pytest_asyncio.fixture
async def db_tenant_repo(async_session):
    """Database tenant repository for parity validation."""
    from adapters.persistence.repositories import SQLAlchemyTenantRepository
    return SQLAlchemyTenantRepository(async_session)


@pytest_asyncio.fixture
async def db_user_repo(async_session):
    """Database user repository for parity validation."""
    from adapters.persistence.repositories import SQLAlchemyUserRepository
    return SQLAlchemyUserRepository(async_session)


@pytest_asyncio.fixture
async def db_policy_repo(async_session):
    """Database policy repository for parity validation."""
    from adapters.persistence.repositories import SQLAlchemyPolicyRepository
    return SQLAlchemyPolicyRepository(async_session)


@pytest_asyncio.fixture
async def db_featureflag_repo(async_session):
    """Database feature flag repository for parity validation."""
    from adapters.persistence.repositories import SQLAlchemyFeatureFlagRepository
    return SQLAlchemyFeatureFlagRepository(async_session)


def pytest_collection_modifyitems(config, items):
    """
    Automatically skip database-specific tests based on current database dialect.
    
    Markers:
    - @pytest.mark.postgres_only: Skip if not using PostgreSQL
    - @pytest.mark.sqlite_only: Skip if not using SQLite
    
    This ensures cross-database test compatibility without manual skip decorators.
    """
    for item in items:
        # Check if test has postgres_only marker
        if item.get_closest_marker("postgres_only"):
            if not DB_CONFIG.is_postgres:
                item.add_marker(
                    pytest.mark.skip(
                        reason=f"Test requires PostgreSQL, current database is {DB_CONFIG.dialect.value}"
                    )
                )
        
        # Check if test has sqlite_only marker
        if item.get_closest_marker("sqlite_only"):
            if not DB_CONFIG.is_sqlite:
                item.add_marker(
                    pytest.mark.skip(
                        reason=f"Test requires SQLite, current database is {DB_CONFIG.dialect.value}"
                    )
                )
