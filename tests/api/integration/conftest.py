"""
API Integration Test Suite - Conftest

Provides fixtures for API integration tests with:
- Fresh PostgreSQL database setup
- Bootstrap + seed data
- Test client with authentication
- Database cleanup between tests
"""
import pytest
import asyncio
import os
import sys
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

# Set test environment BEFORE imports
# DATABASE_URL: Respect env var if set, otherwise use descriptor.toml default (SQLite)
# For PostgreSQL integration tests: export DATABASE_URL="postgresql+asyncpg://infysight_dbadmin:infysight_dbadmin123@localhost/githubspeckit_test"
if "DATABASE_URL" not in os.environ:
    # Use SQLite by default for fast local testing
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_infysight_integration.db"

os.environ["APP_ENV"] = "test"
os.environ["JWT_SECRET_KEY"] = "test_secret_key_min_32_chars_long_for_hs256"
os.environ["ARGON2_TIME_COST"] = "1"  # Fast for testing
os.environ["ARGON2_MEMORY_COST"] = "8"
os.environ["ARGON2_PARALLELISM"] = "1"

import pytest_asyncio

from adapters.api.app import create_app
from adapters.persistence.db_config import DatabaseConfig


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Create database engine for the test session with migrations."""
    import subprocess
    
    # Run migrations to create schema BEFORE creating engine
    # This ensures database has proper schema for all tests
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        env={**os.environ}
    )
    
    if result.returncode != 0:
        pytest.fail(f"Failed to run migrations: {result.stderr}")
    
    db_config = DatabaseConfig.from_env()
    engine = db_config.create_engine()
    
    yield engine
    
    # Properly dispose of the engine and wait for connections to close
    await engine.dispose()
    # Give time for connection pool cleanup
    await asyncio.sleep(0.1)


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test with cleanup."""
    async_session_maker = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
        # Rollback any changes
        await session.rollback()


@pytest_asyncio.fixture(scope="session")
async def seeded_database(db_engine):
    """
    Seed the database once per test session.
    
    Creates:
    - Tenant: infysight
    - Superadmin: infysightsa@infysight.com / infysightsa123
    - Tenant Admin: infysightadmin@infysight.com / infysightadmin123
    - Standard User: infysightuser@infysight.com / infysightuser123
    """
    from datetime import datetime, timezone
    import uuid
    from adapters.persistence.repositories import (
        SQLAlchemyTenantRepository,
        SQLAlchemyUserRepository,
    )
    from domain.tenants.models import Tenant, TenantStatus
    from domain.users.models import User, UserStatus
    from auth_core.hashers import default_hasher
    
    # Deterministic UUID namespace for infysight
    INFYSIGHT_NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")
    
    def deterministic_uuid(name: str) -> str:
        """Generate deterministic UUIDv5 from name."""
        return str(uuid.uuid5(INFYSIGHT_NAMESPACE, name))
    
    async_session_maker = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    tenant_id = deterministic_uuid("tenant:infysight")
    superadmin_id = deterministic_uuid("user:infysightsa@infysight.com")
    tenant_admin_id = deterministic_uuid("user:infysightadmin@infysight.com")
    standard_user_id = deterministic_uuid("user:infysightuser@infysight.com")
    
    async with async_session_maker() as session:
        async with session.begin():
            tenant_repo = SQLAlchemyTenantRepository(session)
            user_repo = SQLAlchemyUserRepository(session)
            
            # Create tenant
            tenant = Tenant(
                tenant_id=tenant_id,
                name="infysight",
                status=TenantStatus.active,
                config_version=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                created_by=None,
                updated_by=None,
            )
            await tenant_repo.upsert(tenant)
            
            # Create superadmin user
            superadmin = User(
                user_id=superadmin_id,
                tenant_id=tenant_id,
                email="infysightsa@infysight.com",
                status=UserStatus.active,
                roles=["superadmin"],
                password_hash=default_hasher.hash("infysightsa123"),
                last_login_at=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                created_by=None,
                updated_by=None,
            )
            await user_repo.upsert(superadmin)
            
            # Create tenant_admin user
            tenant_admin = User(
                user_id=tenant_admin_id,
                tenant_id=tenant_id,
                email="infysightadmin@infysight.com",
                status=UserStatus.active,
                roles=["tenant_admin"],
                password_hash=default_hasher.hash("infysightadmin123"),
                last_login_at=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                created_by=None,
                updated_by=None,
            )
            await user_repo.upsert(tenant_admin)
            
            # Create standard user
            standard_user = User(
                user_id=standard_user_id,
                tenant_id=tenant_id,
                email="infysightuser@infysight.com",
                status=UserStatus.active,
                roles=["standard"],
                password_hash=default_hasher.hash("infysightuser123"),
                last_login_at=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                created_by=None,
                updated_by=None,
            )
            await user_repo.upsert(standard_user)
    
    return {
        "tenant_id": tenant_id,
        "user_id": superadmin_id,
        "tenant_admin_id": tenant_admin_id,
        "standard_user_id": standard_user_id,
    }


@pytest_asyncio.fixture
async def api_client(seeded_database) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with seeded database."""
    app = create_app()
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def superadmin_token(api_client: AsyncClient) -> str:
    """Get authentication token for superadmin user."""
    response = await api_client.post(
        "/api/v1/auth/login",
        json={
            "email": "infysightsa@infysight.com",
            "password": "infysightsa123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    return data["access_token"]


@pytest_asyncio.fixture
async def tenant_admin_token(api_client: AsyncClient) -> str:
    """Get authentication token for tenant admin user."""
    response = await api_client.post(
        "/api/v1/auth/login",
        json={
            "email": "infysightadmin@infysight.com",
            "password": "infysightadmin123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    return data["access_token"]


@pytest_asyncio.fixture
async def standard_user_token(api_client: AsyncClient) -> str:
    """Get authentication token for standard user."""
    response = await api_client.post(
        "/api/v1/auth/login",
        json={
            "email": "infysightuser@infysight.com",
            "password": "infysightuser123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    return data["access_token"]


@pytest_asyncio.fixture
async def auth_headers(superadmin_token: str) -> dict:
    """Get authorization headers with superadmin token."""
    return {"Authorization": f"Bearer {superadmin_token}"}


@pytest_asyncio.fixture
async def tenant_admin_headers(tenant_admin_token: str) -> dict:
    """Get authorization headers with tenant admin token."""
    return {"Authorization": f"Bearer {tenant_admin_token}"}


@pytest_asyncio.fixture
async def standard_user_headers(standard_user_token: str) -> dict:
    """Get authorization headers with standard user token."""
    return {"Authorization": f"Bearer {standard_user_token}"}
