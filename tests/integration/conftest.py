"""
Fixtures for integration tests.

Provides sample entities (tenants, users) for testing.
"""
import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone

from src.domain.tenants.models import Tenant, TenantStatus
from src.domain.users.models import User, UserStatus
from src.adapters.persistence.repositories import (
    SQLAlchemyTenantRepository,
    SQLAlchemyUserRepository,
)


@pytest.fixture
async def sample_tenant(db_session):
    """Create a sample tenant for testing."""
    repo = SQLAlchemyTenantRepository(db_session)
    
    tenant = Tenant(
        tenant_id=str(uuid4()),
        name=f"test_tenant_{uuid4().hex[:8]}",
        status=TenantStatus.active,
        config_version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        created_by="system",
        updated_by="system",
    )
    
    created = await repo.upsert(tenant)
    return created


@pytest.fixture
async def sample_user(db_session, sample_tenant):
    """Create a sample user for testing."""
    repo = SQLAlchemyUserRepository(db_session)
    
    # Convert string tenant_id to UUID for user creation
    tenant_uuid = UUID(sample_tenant.tenant_id)
    
    user = User(
        user_id=str(uuid4()),
        tenant_id=str(tenant_uuid),
        email=f"test_{uuid4().hex[:8]}@example.com",
        status=UserStatus.active,
        roles=[],
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$dummy",  # Dummy hash
        last_login_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        created_by=str(tenant_uuid),
        updated_by=str(tenant_uuid),
    )
    
    created = await repo.upsert(user)
    return created
