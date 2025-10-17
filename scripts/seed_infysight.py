#!/usr/bin/env python3
"""
Seed script for infysight tenant and superadmin user.

Creates:
- Tenant: infysight
- User: infysightsa (superadmin role)
- Password: infysightsa123

Usage:
    python scripts/seed_infysight.py
"""
import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from datetime import datetime, timezone
import uuid

from adapters.persistence.repositories import (
    SQLAlchemyTenantRepository,
    SQLAlchemyUserRepository,
)
from adapters.persistence.models import TenantStatusEnum, UserStatusEnum
from domain.tenants.models import Tenant, TenantStatus
from domain.users.models import User, UserStatus
from auth_core.hashers import default_hasher

# Import script logger
sys.path.insert(0, os.path.dirname(__file__))
from script_logger import get_logger

logger = get_logger("seed_infysight")


# Deterministic UUID namespace for infysight
INFYSIGHT_NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")


def deterministic_uuid(name: str) -> str:
    """Generate deterministic UUIDv5 from name."""
    return str(uuid.uuid5(INFYSIGHT_NAMESPACE, name))


async def seed_infysight():
    """Seed infysight tenant and superadmin user."""
    
    # Database connection from environment or default
    # NOTE: Script exception - direct os.getenv() allowed for operational scripts
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://infysight_dbadmin:infysight_dbadmin123@localhost/infysight_users")
    
    # Mask sensitive parts of URL for logging
    masked_url = database_url.split('@')[1] if '@' in database_url else database_url
    logger.info("database_connection", url=masked_url)
    
    # Create async engine and session
    engine = create_async_engine(database_url, echo=False)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Generate deterministic IDs
    tenant_id = deterministic_uuid("tenant:infysight")
    user_id = deterministic_uuid("user:infysightsa@infysight.com")
    
    logger.info("generated_ids", tenant_id=tenant_id, user_id=user_id)
    
    # Hash the password
    password_hash = default_hasher.hash("infysightsa123")
    logger.info("password_hashed")
    
    async with async_session_maker() as session:
        async with session.begin():
            # Initialize repositories
            tenant_repo = SQLAlchemyTenantRepository(session)
            user_repo = SQLAlchemyUserRepository(session)
            
            # Check and create tenant
            existing_tenant = await tenant_repo.get(tenant_id)
            if existing_tenant:
                logger.warning("tenant_exists", tenant_id=tenant_id, name="infysight")
            else:
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
                logger.success("tenant_created", tenant_id=tenant_id, name="infysight")
            
            # Check and create admin user
            existing_user = await user_repo.get(user_id)
            if existing_user:
                logger.warning("user_exists", user_id=user_id, email="infysightsa@infysight.com")
                # Update password if user exists
                existing_user.password_hash = password_hash
                await user_repo.upsert(existing_user)
                logger.info("password_updated", user_id=user_id)
            else:
                user = User(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    email="infysightsa@infysight.com",
                    status=UserStatus.active,
                    roles=["superadmin"],
                    password_hash=password_hash,
                    last_login_at=None,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    created_by=None,
                    updated_by=None,
                )
                await user_repo.upsert(user)
                logger.success("user_created", user_id=user_id, email="infysightsa@infysight.com", role="superadmin")
    
    await engine.dispose()
    
    logger.success("seed_complete")
    
    # Output credentials in structured format
    credentials = {
        "username": "infysightsa",
        "email": "infysightsa@infysight.com",
        "password": "infysightsa123",
        "role": "superadmin",
        "tenant": "infysight",
        "tenant_id": tenant_id,
        "user_id": user_id
    }
    logger.json_output(credentials)


async def main():
    """Main entry point."""
    try:
        await seed_infysight()
        sys.exit(0)
    except Exception as e:
        logger.error("seed_failed", error=str(e), error_type=type(e).__name__)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
