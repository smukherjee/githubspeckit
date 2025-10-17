"""
Integration tests for user update RBAC authorization rules.

Tests three authorization levels as per constitutional principles:
1. Superadmin: Can update any user across all tenants
2. Tenant admin: Can update any user within their own tenant only
3. Regular user: Can update only their own profile (email only)

These tests verify the API-layer authorization is frontend-agnostic and properly enforced.
"""
import pytest
from httpx import AsyncClient
from fastapi import status
from uuid import uuid5, UUID


# Deterministic UUID generation
INFYSIGHT_NAMESPACE = UUID("12345678-1234-5678-1234-567812345678")
OTHER_TENANT_NAMESPACE = UUID("87654321-4321-8765-4321-876543218765")


def deterministic_uuid(name: str, namespace: UUID = INFYSIGHT_NAMESPACE) -> str:
    """Generate deterministic UUID for testing."""
    return str(uuid5(namespace, name))


@pytest.mark.asyncio
class TestSuperadminUpdateRBAC:
    """Test superadmin authorization: Can update any user across all tenants."""

    async def test_superadmin_can_update_any_user_same_tenant(
        self, client: AsyncClient, superadmin_headers: dict, regular_user_id: str
    ):
        """Superadmin can update users in their own tenant."""
        response = await client.put(
            f"/api/v1/users/{regular_user_id}",
            headers=superadmin_headers,
            json={"email": "updated_user@infysight.com"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "updated_user@infysight.com"

    async def test_superadmin_can_update_roles_for_other_users(
        self, client: AsyncClient, superadmin_headers: dict, regular_user_id: str
    ):
        """Superadmin can modify roles for other users."""
        response = await client.put(
            f"/api/v1/users/{regular_user_id}",
            headers=superadmin_headers,
            json={"roles": ["tenant_admin", "analyst"]}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "tenant_admin" in data["roles"]
        assert "analyst" in data["roles"]

    async def test_superadmin_can_disable_other_users(
        self, client: AsyncClient, superadmin_headers: dict, regular_user_id: str
    ):
        """Superadmin can disable/enable other user accounts."""
        response = await client.put(
            f"/api/v1/users/{regular_user_id}",
            headers=superadmin_headers,
            json={"is_disabled": True}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Status field is used instead of is_disabled
        assert data["status"] == "disabled"

    async def test_superadmin_cannot_change_own_roles(
        self, client: AsyncClient, superadmin_headers: dict, test_user_id: str
    ):
        """Superadmin cannot modify their own roles (self-protection)."""
        response = await client.put(
            f"/api/v1/users/{test_user_id}",
            headers=superadmin_headers,
            json={"roles": ["superadmin", "tenant_admin"]}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "Cannot modify your own roles" in data["detail"]

    async def test_superadmin_cannot_change_own_status(
        self, client: AsyncClient, superadmin_headers: dict, test_user_id: str
    ):
        """Superadmin cannot disable their own account (self-protection)."""
        response = await client.put(
            f"/api/v1/users/{test_user_id}",
            headers=superadmin_headers,
            json={"is_disabled": True}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "Cannot modify your own" in data["detail"]

    async def test_superadmin_can_update_own_email(
        self, client: AsyncClient, superadmin_headers: dict, test_user_id: str
    ):
        """Superadmin can update their own email."""
        response = await client.put(
            f"/api/v1/users/{test_user_id}",
            headers=superadmin_headers,
            json={"email": "newsuperadmin@infysight.com"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "newsuperadmin@infysight.com"


@pytest.mark.asyncio
class TestTenantAdminUpdateRBAC:
    """Test tenant admin authorization: Can update users within their own tenant only."""

    async def test_tenant_admin_can_update_user_same_tenant(
        self, client: AsyncClient, tenant_admin_headers: dict, regular_user_id: str
    ):
        """Tenant admin can update users in their own tenant."""
        response = await client.put(
            f"/api/v1/users/{regular_user_id}",
            headers=tenant_admin_headers,
            json={"email": "updated_by_admin@infysight.com"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "updated_by_admin@infysight.com"

    async def test_tenant_admin_can_update_roles_same_tenant(
        self, client: AsyncClient, tenant_admin_headers: dict, regular_user_id: str
    ):
        """Tenant admin can modify roles for users in their tenant."""
        response = await client.put(
            f"/api/v1/users/{regular_user_id}",
            headers=tenant_admin_headers,
            json={"roles": ["analyst", "developer"]}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "analyst" in data["roles"]
        assert "developer" in data["roles"]

    async def test_tenant_admin_can_disable_user_same_tenant(
        self, client: AsyncClient, tenant_admin_headers: dict, regular_user_id: str
    ):
        """Tenant admin can disable users in their tenant."""
        response = await client.put(
            f"/api/v1/users/{regular_user_id}",
            headers=tenant_admin_headers,
            json={"is_disabled": True}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Status field is used instead of is_disabled
        assert data["status"] == "disabled"

    async def test_tenant_admin_cannot_update_user_different_tenant(
        self, client: AsyncClient, tenant_admin_headers: dict, db_engine
    ):
        """Tenant admin CANNOT update users in different tenants."""
        from datetime import datetime, timezone
        from adapters.persistence.repositories import (
            SQLAlchemyTenantRepository,
            SQLAlchemyUserRepository,
        )
        from domain.tenants.models import Tenant, TenantStatus
        from domain.users.models import User, UserStatus
        from auth_core.hashers import default_hasher
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
        
        # Create a different tenant and user
        async_session_maker = async_sessionmaker(
            bind=db_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        other_tenant_id = deterministic_uuid("tenant:other", OTHER_TENANT_NAMESPACE)
        other_user_id = deterministic_uuid("user:other@other.com", OTHER_TENANT_NAMESPACE)
        
        async with async_session_maker() as session:
            async with session.begin():
                tenant_repo = SQLAlchemyTenantRepository(session)
                user_repo = SQLAlchemyUserRepository(session)
                
                # Create other tenant
                other_tenant = Tenant(
                    tenant_id=other_tenant_id,
                    name="other_company",
                    status=TenantStatus.active,
                    config_version=1,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    created_by=None,
                    updated_by=None,
                )
                await tenant_repo.upsert(other_tenant)
                
                # Create user in other tenant
                other_user = User(
                    user_id=other_user_id,
                    tenant_id=other_tenant_id,
                    email="otheruser@other.com",
                    status=UserStatus.active,
                    roles=["user"],  # Use valid role 'user' instead of 'standard'
                    password_hash=default_hasher.hash("otheruser123"),
                    last_login_at=None,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    created_by=None,
                    updated_by=None,
                )
                await user_repo.upsert(other_user)
        
        # Attempt to update user in different tenant
        response = await client.put(
            f"/api/v1/users/{other_user_id}",
            headers=tenant_admin_headers,
            json={"email": "hacked@infysight.com"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "can only update users in their own tenant" in data["detail"]

    async def test_tenant_admin_cannot_modify_superadmin_users(
        self, client: AsyncClient, tenant_admin_headers: dict, test_user_id: str
    ):
        """Tenant admin CANNOT modify superadmin users even in same tenant."""
        response = await client.put(
            f"/api/v1/users/{test_user_id}",
            headers=tenant_admin_headers,
            json={"email": "hacked_superadmin@infysight.com"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "Only superadmins can modify superadmin users" in data["detail"]

    async def test_tenant_admin_cannot_change_own_roles(
        self, client: AsyncClient, tenant_admin_headers: dict, same_tenant_user_id: str
    ):
        """Tenant admin cannot modify their own roles (self-protection)."""
        response = await client.put(
            f"/api/v1/users/{same_tenant_user_id}",
            headers=tenant_admin_headers,
            json={"roles": ["superadmin"]}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "Cannot modify your own roles" in data["detail"]

    async def test_tenant_admin_cannot_change_own_status(
        self, client: AsyncClient, tenant_admin_headers: dict, same_tenant_user_id: str
    ):
        """Tenant admin cannot disable their own account (self-protection)."""
        response = await client.put(
            f"/api/v1/users/{same_tenant_user_id}",
            headers=tenant_admin_headers,
            json={"is_disabled": True}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "Cannot modify your own" in data["detail"]

    async def test_tenant_admin_can_update_own_email(
        self, client: AsyncClient, tenant_admin_headers: dict, same_tenant_user_id: str
    ):
        """Tenant admin can update their own email."""
        response = await client.put(
            f"/api/v1/users/{same_tenant_user_id}",
            headers=tenant_admin_headers,
            json={"email": "newadmin@infysight.com"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "newadmin@infysight.com"


@pytest.mark.asyncio
class TestRegularUserUpdateRBAC:
    """Test regular user authorization: Can update only their own profile (email only)."""

    async def test_regular_user_can_update_own_email(
        self, client: AsyncClient, regular_user_headers: dict, regular_user_id: str
    ):
        """Regular user can update their own email."""
        response = await client.put(
            f"/api/v1/users/{regular_user_id}",
            headers=regular_user_headers,
            json={"email": "mynewemail@infysight.com"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "mynewemail@infysight.com"

    async def test_regular_user_cannot_update_own_roles(
        self, client: AsyncClient, regular_user_headers: dict, regular_user_id: str
    ):
        """Regular user CANNOT modify their own roles."""
        response = await client.put(
            f"/api/v1/users/{regular_user_id}",
            headers=regular_user_headers,
            json={"roles": ["tenant_admin", "superadmin"]}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "Cannot modify your own roles" in data["detail"]

    async def test_regular_user_cannot_update_own_status(
        self, client: AsyncClient, regular_user_headers: dict, regular_user_id: str
    ):
        """Regular user CANNOT disable/enable their own account."""
        response = await client.put(
            f"/api/v1/users/{regular_user_id}",
            headers=regular_user_headers,
            json={"is_disabled": False}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "Cannot modify your own" in data["detail"]

    async def test_regular_user_cannot_update_other_user_same_tenant(
        self, client: AsyncClient, regular_user_headers: dict, same_tenant_user_id: str
    ):
        """Regular user CANNOT update other users even in same tenant."""
        response = await client.put(
            f"/api/v1/users/{same_tenant_user_id}",
            headers=regular_user_headers,
            json={"email": "hacked@infysight.com"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "Regular users can only update their own profile" in data["detail"]

    async def test_regular_user_cannot_update_superadmin(
        self, client: AsyncClient, regular_user_headers: dict, test_user_id: str
    ):
        """Regular user CANNOT update superadmin users."""
        response = await client.put(
            f"/api/v1/users/{test_user_id}",
            headers=regular_user_headers,
            json={"email": "hacked_sa@infysight.com"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "Regular users can only update their own profile" in data["detail"]


@pytest.mark.asyncio
class TestCrossScenarioUpdateRBAC:
    """Test complex cross-scenario authorization rules."""

    async def test_role_escalation_prevention_tenant_admin(
        self, client: AsyncClient, tenant_admin_headers: dict, regular_user_id: str
    ):
        """Tenant admin cannot assign superadmin role to users."""
        response = await client.put(
            f"/api/v1/users/{regular_user_id}",
            headers=tenant_admin_headers,
            json={"roles": ["superadmin", "tenant_admin"]}
        )
        
        # Should fail at role escalation check (after RBAC auth passes)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        # This should be caught by role escalation logic, not RBAC
        assert "superadmin" in data["detail"].lower()

    async def test_combined_update_regular_user(
        self, client: AsyncClient, regular_user_headers: dict, regular_user_id: str
    ):
        """Regular user cannot combine email update with role/status changes."""
        response = await client.put(
            f"/api/v1/users/{regular_user_id}",
            headers=regular_user_headers,
            json={
                "email": "newemail@infysight.com",
                "roles": ["tenant_admin"]
            }
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "Cannot modify your own roles" in data["detail"]

    async def test_nonexistent_user_update_permissions(
        self, client: AsyncClient, regular_user_headers: dict
    ):
        """Proper error handling for nonexistent user updates."""
        fake_user_id = deterministic_uuid("user:fake@fake.com")
        
        response = await client.put(
            f"/api/v1/users/{fake_user_id}",
            headers=regular_user_headers,
            json={"email": "test@test.com"}
        )
        
        # Should return 404 or 403 depending on auth check order
        # (404 is expected as user lookup happens before most RBAC checks)
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    async def test_unauthenticated_update_denied(self, client: AsyncClient, regular_user_id: str):
        """Unauthenticated requests cannot update users."""
        response = await client.put(
            f"/api/v1/users/{regular_user_id}",
            json={"email": "hacker@evil.com"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_invalid_token_update_denied(self, client: AsyncClient, regular_user_id: str):
        """Invalid tokens cannot update users."""
        response = await client.put(
            f"/api/v1/users/{regular_user_id}",
            headers={"Authorization": "Bearer invalid_token_xyz"},
            json={"email": "hacker@evil.com"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
