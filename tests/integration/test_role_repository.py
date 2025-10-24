"""
Integration tests for RoleRepository (T083 validation).

Tests SQLAlchemyRoleRepository implementation with actual database.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timezone

from src.adapters.persistence.repositories import SQLAlchemyRoleRepository
from src.domain.roles.entities import Role, SYSTEM_ROLE_IDS
from src.domain.roles.exceptions import (
    RoleNotFoundError,
    DuplicateRoleNameError,
    SystemRoleImmutableError,
)
from src.domain.roles.permissions import Permission


@pytest.mark.asyncio
class TestRoleRepositoryBasicCRUD:
    """Test basic CRUD operations for role repository."""

    async def test_get_system_role_by_id(self, db_session):
        """Test retrieving system role by ID."""
        repo = SQLAlchemyRoleRepository(db_session)
        
        # Get superadmin system role
        role = await repo.get_by_id(SYSTEM_ROLE_IDS["superadmin"])
        
        assert role is not None
        assert role.name == "superadmin"
        assert role.is_system is True
        assert role.tenant_id is None
        assert Permission.ALL in role.permissions

    async def test_get_by_name_system_role(self, db_session):
        """Test retrieving system role by name."""
        repo = SQLAlchemyRoleRepository(db_session)
        
        role = await repo.get_by_name("tenant_admin", tenant_id=None)
        
        assert role is not None
        assert role.name == "tenant_admin"
        assert role.is_system is True
        assert "tenant:*" in role.permissions

    async def test_list_all_roles_includes_system(self, db_session):
        """Test listing all roles includes system roles."""
        repo = SQLAlchemyRoleRepository(db_session)
        
        roles = await repo.list_all(include_system=True)
        
        assert len(roles) >= 3  # At least 3 system roles
        role_names = [r.name for r in roles]
        assert "superadmin" in role_names
        assert "tenant_admin" in role_names
        assert "user" in role_names

    async def test_create_custom_role(self, db_session, sample_tenant):
        """Test creating a custom tenant role."""
        repo = SQLAlchemyRoleRepository(db_session)
        
        # Convert string tenant_id to UUID
        from uuid import UUID
        tenant_uuid = UUID(sample_tenant.tenant_id)
        
        new_role = Role(
            id=uuid4(),
            name="analyst",
            tenant_id=tenant_uuid,
            is_system=False,
            permissions=["users:read", "reports:read"],
            description="Analyst role with read-only access",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        created = await repo.create(new_role)
        
        assert created.id == new_role.id
        assert created.name == "analyst"
        assert created.tenant_id == tenant_uuid
        assert created.is_system is False
        assert "users:read" in created.permissions

    async def test_create_duplicate_role_name_raises_error(self, db_session, sample_tenant):
        """Test that creating a role with duplicate name raises error."""
        repo = SQLAlchemyRoleRepository(db_session)
        
        # Convert string tenant_id to UUID
        from uuid import UUID
        tenant_uuid = UUID(sample_tenant.tenant_id)
        
        # Create first role
        role1 = Role(
            id=uuid4(),
            name="duplicate_test",
            tenant_id=tenant_uuid,
            is_system=False,
            permissions=["users:read"],
            description="First role",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await repo.create(role1)
        
        # Try to create second role with same name
        role2 = Role(
            id=uuid4(),
            name="duplicate_test",
            tenant_id=tenant_uuid,
            is_system=False,
            permissions=["users:update"],  # Valid permission
            description="Second role (should fail)",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        with pytest.raises(DuplicateRoleNameError):
            await repo.create(role2)


@pytest.mark.asyncio
class TestRoleRepositorySystemRoleProtection:
    """Test system role immutability protection."""

    async def test_cannot_update_system_role(self, db_session):
        """Test that system roles cannot be modified."""
        repo = SQLAlchemyRoleRepository(db_session)
        
        # Get system role
        role = await repo.get_by_id(SYSTEM_ROLE_IDS["user"])
        assert role is not None
        
        # Try to update it
        role.permissions.append("dangerous:permission")
        
        with pytest.raises(SystemRoleImmutableError):
            await repo.update(role)

    async def test_cannot_delete_system_role(self, db_session):
        """Test that system roles cannot be deleted."""
        repo = SQLAlchemyRoleRepository(db_session)
        
        with pytest.raises(SystemRoleImmutableError):
            await repo.delete(SYSTEM_ROLE_IDS["superadmin"])


@pytest.mark.asyncio
class TestRoleRepositoryUserAssignment:
    """Test role assignment and revocation."""

    async def test_assign_role_to_user(self, db_session, sample_user):
        """Test assigning a role to a user."""
        repo = SQLAlchemyRoleRepository(db_session)
        
        # Convert string user_id to UUID
        from uuid import UUID
        user_uuid = UUID(sample_user.user_id)
        
        # Assign superadmin role
        await repo.assign_to_user(
            user_id=user_uuid,
            role_id=SYSTEM_ROLE_IDS["superadmin"],
            assigned_by=user_uuid,
        )
        
        # Verify assignment
        user_roles = await repo.get_user_roles(user_uuid)
        role_names = [r.name for r in user_roles]
        assert "superadmin" in role_names

    async def test_revoke_role_from_user(self, db_session, sample_user):
        """Test revoking a role from a user."""
        repo = SQLAlchemyRoleRepository(db_session)
        
        # Convert string user_id to UUID
        from uuid import UUID
        user_uuid = UUID(sample_user.user_id)
        
        # Assign role first
        await repo.assign_to_user(
            user_id=user_uuid,
            role_id=SYSTEM_ROLE_IDS["tenant_admin"],
        )
        
        # Verify assignment
        user_roles = await repo.get_user_roles(user_uuid)
        assert len(user_roles) > 0
        
        # Revoke role
        await repo.revoke_from_user(
            user_id=user_uuid,
            role_id=SYSTEM_ROLE_IDS["tenant_admin"],
        )
        
        # Verify revocation
        user_roles_after = await repo.get_user_roles(user_uuid)
        role_names = [r.name for r in user_roles_after]
        assert "tenant_admin" not in role_names

    async def test_count_role_users(self, db_session, sample_user):
        """Test counting users with a specific role."""
        repo = SQLAlchemyRoleRepository(db_session)
        
        # Convert string user_id to UUID
        from uuid import UUID
        user_uuid = UUID(sample_user.user_id)
        
        # Count before assignment
        count_before = await repo.count_role_users(SYSTEM_ROLE_IDS["user"])
        
        # Assign role
        await repo.assign_to_user(
            user_id=user_uuid,
            role_id=SYSTEM_ROLE_IDS["user"],
        )
        
        # Count after assignment
        count_after = await repo.count_role_users(SYSTEM_ROLE_IDS["user"])
        
        assert count_after == count_before + 1
