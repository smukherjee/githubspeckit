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
    """Seed infysight tenant and all test users (superadmin, tenant_admin, user)."""
    
    # Database connection from environment or default
    # NOTE: Script exception - direct os.getenv() allowed for operational scripts
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://infysight_dbadmin:infysight_dbadmin123@localhost/infysight_users")
    
    # Mask sensitive parts of URL for logging
    masked_url = database_url.split('@')[1] if '@' in database_url else database_url
    logger.info("database_connection", url=masked_url)
    
    # Create async engine and session
    engine = create_async_engine(database_url, echo=False)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Generate deterministic IDs for all 3 test users
    tenant_id = deterministic_uuid("tenant:infysight")
    superadmin_id = deterministic_uuid("user:infysightsa@infysight.com")
    tenant_admin_id = deterministic_uuid("user:infysightadmin@infysight.com")
    standard_user_id = deterministic_uuid("user:infysightuser@infysight.com")
    
    logger.info("generated_ids", 
                tenant_id=tenant_id, 
                superadmin_id=superadmin_id,
                tenant_admin_id=tenant_admin_id,
                standard_user_id=standard_user_id)
    
    # Hash all passwords
    superadmin_password = default_hasher.hash("infysightsa123")
    tenant_admin_password = default_hasher.hash("infysightadmin123")
    standard_user_password = default_hasher.hash("infysightuser123")
    logger.info("passwords_hashed")
    
    async with async_session_maker() as session:
        async with session.begin():
            # Initialize repositories
            tenant_repo = SQLAlchemyTenantRepository(session)
            user_repo = SQLAlchemyUserRepository(session)
            
            # Get system role UUIDs by name (FR-122)
            from sqlalchemy import text
            role_uuid_query = text("""
                SELECT id, name FROM roles 
                WHERE is_system = true AND name IN ('superadmin', 'tenant_admin', 'user')
            """)
            role_result = await session.execute(role_uuid_query)
            role_uuid_map = {row[1]: str(row[0]) for row in role_result.all()}
            
            if len(role_uuid_map) != 3:
                logger.error("missing_system_roles", 
                           found=list(role_uuid_map.keys()),
                           expected=["superadmin", "tenant_admin", "user"])
                raise RuntimeError(f"Expected 3 system roles, found {len(role_uuid_map)}")
            
            logger.info("system_roles_loaded", roles=role_uuid_map)
            
            # Define all 3 test users (NOW USING ROLE UUIDs)
            users_to_create = [
                {
                    "user_id": superadmin_id,
                    "email": "infysightsa@infysight.com",
                    "roles": [role_uuid_map["superadmin"]],  # UUID not name
                    "role_names": ["superadmin"],  # For logging
                    "password_hash": superadmin_password,
                    "full_name": "InfySight Superadmin"
                },
                {
                    "user_id": tenant_admin_id,
                    "email": "infysightadmin@infysight.com",
                    "roles": [role_uuid_map["tenant_admin"]],  # UUID not name
                    "role_names": ["tenant_admin"],  # For logging
                    "password_hash": tenant_admin_password,
                    "full_name": "InfySight Tenant Admin"
                },
                {
                    "user_id": standard_user_id,
                    "email": "infysightuser@infysight.com",
                    "roles": [role_uuid_map["user"]],  # UUID not name
                    "role_names": ["user"],  # For logging
                    "password_hash": standard_user_password,
                    "full_name": "InfySight Standard User"
                }
            ]
            
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
            
            # Create all 3 users
            for user_data in users_to_create:
                existing_user = await user_repo.get(user_data["user_id"])
                if existing_user:
                    logger.warning("user_exists", user_id=user_data["user_id"], email=user_data["email"])
                    # Update password AND roles if user exists (fix for role UUID migration)
                    existing_user.password_hash = user_data["password_hash"]
                    existing_user.roles = user_data["roles"]  # Update roles to UUIDs
                    await user_repo.upsert(existing_user)
                    logger.info("user_updated", user_id=user_data["user_id"], roles=user_data["role_names"])
                else:
                    user = User(
                        user_id=user_data["user_id"],
                        tenant_id=tenant_id,
                        email=user_data["email"],
                        status=UserStatus.active,
                        roles=user_data["roles"],
                        password_hash=user_data["password_hash"],
                        last_login_at=None,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                        created_by=None,
                        updated_by=None,
                    )
                    await user_repo.upsert(user)
                    logger.success("user_created", 
                                 user_id=user_data["user_id"], 
                                 email=user_data["email"], 
                                 roles=user_data["role_names"])
            
            # Create user_details for all users (FR-003-user-profile-details)
            # Use raw SQL since domain models aren't implemented yet (T016-T019)
            from sqlalchemy import text
            
            user_details_query = text("""
                INSERT INTO user_details (
                    user_id, full_name, phone, address,
                    photo_display_url, photo_thumbnail_url, photo_avatar_url,
                    created_by, updated_by
                ) VALUES (
                    :user_id, :full_name, NULL, NULL,
                    NULL, NULL, NULL,
                    :user_id, :user_id
                )
                ON CONFLICT (user_id) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = CURRENT_TIMESTAMP
            """)
            
            # Create user_details for all 3 users
            for user_data in users_to_create:
                await session.execute(user_details_query, {
                    "user_id": str(user_data["user_id"]),
                    "full_name": user_data["full_name"]
                })
                logger.success("user_details_created", 
                             user_id=user_data["user_id"], 
                             full_name=user_data["full_name"])
    
    await engine.dispose()
    
    logger.success("seed_complete", users_created=3)
    
    # Output all credentials in structured format
    all_credentials = [
        {
            "username": "infysightsa",
            "email": "infysightsa@infysight.com",
            "password": "infysightsa123",
            "roles": ["superadmin"],
            "tenant": "infysight",
            "tenant_id": tenant_id,
            "user_id": superadmin_id
        },
        {
            "username": "infysightadmin",
            "email": "infysightadmin@infysight.com",
            "password": "infysightadmin123",
            "roles": ["tenant_admin"],
            "tenant": "infysight",
            "tenant_id": tenant_id,
            "user_id": tenant_admin_id
        },
        {
            "username": "infysightuser",
            "email": "infysightuser@infysight.com",
            "password": "infysightuser123",
            "roles": ["user"],
            "tenant": "infysight",
            "tenant_id": tenant_id,
            "user_id": standard_user_id
        }
    ]
    
    # Output primary superadmin credentials (for backwards compatibility)
    logger.json_output(all_credentials[0])
    
    # Log summary of all created users
    logger.info("all_users_created", 
                superadmin=all_credentials[0]["email"],
                tenant_admin=all_credentials[1]["email"],
                standard_user=all_credentials[2]["email"])


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
