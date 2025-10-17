"""Pytest configuration and fixtures for test suite."""
import pytest
import pytest_asyncio
import asyncio
import os
import sys
from typing import Generator, AsyncGenerator
from httpx import AsyncClient, ASGITransport
from uuid import uuid4, uuid5, UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from adapters.api import deps
from adapters.api.app import create_app

# Set test environment
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"

os.environ["APP_ENV"] = "test"
os.environ["JWT_SECRET_KEY"] = "test_secret_key_min_32_chars_long_for_hs256"
os.environ["ARGON2_TIME_COST"] = "1"
os.environ["ARGON2_MEMORY_COST"] = "8"
os.environ["ARGON2_PARALLELISM"] = "1"


@pytest.fixture(autouse=True)
def reset_session_maker() -> Generator[None, None, None]:
    """Reset the global session maker between tests to avoid event loop issues."""
    # Clear the global session maker before each test
    deps._session_maker = None
    deps._db_config = None
    
    yield
    
    # Clean up after test
    deps._session_maker = None
    deps._db_config = None


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Create database engine for the test session with migrations."""
    import subprocess
    
    # Run migrations
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        env={**os.environ}
    )
    
    if result.returncode != 0:
        pytest.fail(f"Failed to run migrations: {result.stderr}")
    
    from adapters.persistence.db_config import DatabaseConfig
    db_config = DatabaseConfig.from_env()
    engine = db_config.create_engine()
    
    yield engine
    
    await engine.dispose()
    await asyncio.sleep(0.1)


@pytest_asyncio.fixture(scope="session")
async def seeded_database(db_engine):
    """Seed database with test users."""
    from datetime import datetime, timezone
    from adapters.persistence.repositories import (
        SQLAlchemyTenantRepository,
        SQLAlchemyUserRepository,
    )
    from domain.tenants.models import Tenant, TenantStatus
    from domain.users.models import User, UserStatus
    from auth_core.hashers import default_hasher
    
    INFYSIGHT_NAMESPACE = UUID("12345678-1234-5678-1234-567812345678")
    
    def deterministic_uuid(name: str) -> str:
        return str(uuid5(INFYSIGHT_NAMESPACE, name))
    
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
            
            # Create superadmin
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
            
            # Create tenant admin
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
                roles=["user"],  # Use valid role 'user' instead of 'standard'
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
async def client(seeded_database) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with seeded database."""
    app = create_app()
    transport = ASGITransport(app=app)
    
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Provide superadmin authentication headers."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "infysightsa@infysight.com",
            "password": "infysightsa123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest_asyncio.fixture
def test_user_id(seeded_database) -> str:
    """Return superadmin user ID."""
    return seeded_database["user_id"]


@pytest_asyncio.fixture
async def regular_user_headers(client: AsyncClient) -> dict:
    """Provide standard user authentication headers."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "infysightuser@infysight.com",
            "password": "infysightuser123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest_asyncio.fixture
def regular_user_id(seeded_database) -> str:
    """Return standard user ID."""
    return seeded_database["standard_user_id"]


@pytest_asyncio.fixture
async def tenant_admin_headers(client: AsyncClient) -> dict:
    """Provide tenant admin authentication headers."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "infysightadmin@infysight.com",
            "password": "infysightadmin123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest_asyncio.fixture
def same_tenant_user_id(seeded_database) -> str:
    """Return tenant admin user ID (same tenant as standard user)."""
    return seeded_database["tenant_admin_id"]


@pytest_asyncio.fixture
async def superadmin_headers(client: AsyncClient) -> dict:
    """Provide superadmin authentication headers."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "infysightsa@infysight.com",
            "password": "infysightsa123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    return {"Authorization": f"Bearer {data['access_token']}"}

