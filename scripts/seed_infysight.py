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


# Deterministic UUID namespace for infysight
INFYSIGHT_NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")


def deterministic_uuid(name: str) -> str:
    """Generate deterministic UUIDv5 from name."""
    return str(uuid.uuid5(INFYSIGHT_NAMESPACE, name))


async def seed_infysight():
    """Seed infysight tenant and superadmin user."""
    
    # Database connection
    database_url = "postgresql+asyncpg://infysight_dbadmin:infysight_dbadmin123@localhost/infysight_users"
    
    print(f"🔌 Connecting to database: {database_url.split('@')[1]}")
    
    # Create async engine and session
    engine = create_async_engine(database_url, echo=False)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Generate deterministic IDs
    tenant_id = deterministic_uuid("tenant:infysight")
    user_id = deterministic_uuid("user:infysightsa@infysight.com")
    
    print(f"\n📋 Generated IDs:")
    print(f"   Tenant ID: {tenant_id}")
    print(f"   User ID: {user_id}")
    
    # Hash the password
    password_hash = default_hasher.hash("infysightsa123")
    print(f"\n🔐 Password hashed successfully")
    
    async with async_session_maker() as session:
        async with session.begin():
            # Initialize repositories
            tenant_repo = SQLAlchemyTenantRepository(session)
            user_repo = SQLAlchemyUserRepository(session)
            
            # Check and create tenant
            existing_tenant = await tenant_repo.get(tenant_id)
            if existing_tenant:
                print(f"\n⚠️  Tenant 'infysight' already exists (idempotent)")
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
                print(f"\n✅ Created tenant: infysight")
            
            # Check and create admin user
            existing_user = await user_repo.get(user_id)
            if existing_user:
                print(f"⚠️  User 'infysightsa' already exists (idempotent)")
                # Update password if user exists
                existing_user.password_hash = password_hash
                await user_repo.upsert(existing_user)
                print(f"   Password updated for existing user")
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
                print(f"✅ Created user: infysightsa (superadmin)")
    
    await engine.dispose()
    
    print(f"\n🎉 Seed complete!")
    print(f"\n📝 Login credentials:")
    print(f"   Username: infysightsa")
    print(f"   Email: infysightsa@infysight.com")
    print(f"   Password: infysightsa123")
    print(f"   Role: superadmin")
    print(f"   Tenant: infysight")


async def main():
    """Main entry point."""
    try:
        await seed_infysight()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
