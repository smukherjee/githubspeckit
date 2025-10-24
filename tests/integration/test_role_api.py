"""
Integration tests for role management API (FR-122 V1.0).

Tests full lifecycle: create, retrieve, update, delete, assign, revoke.
Validates tenant isolation, permission-based RBAC, audit logging.
"""

import pytest
from uuid import uuid4, UUID
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.domain.roles.permissions import Permission
from src.adapters.persistence.models import RoleModel, UserRoleModel

# System role UUIDs (from migration 20251020_1748_31a51a6816b1_seed_system_roles.py)
SYSTEM_ROLE_IDS = {
    "superadmin": UUID("00000000-0000-0000-0000-000000000001"),
    "tenant_admin": UUID("00000000-0000-0000-0000-000000000002"),
    "user": UUID("00000000-0000-0000-0000-000000000003")
}


@pytest.mark.asyncio
class TestRoleAPIIntegration:
    """Integration tests for role management API with database validation."""

    @pytest.fixture
    async def custom_role_id(
        self, test_client: AsyncClient, admin_token: str, test_tenant_id: str
    ) -> str:
        """Create a custom role and return its ID."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {
            "name": f"integration_test_role_{uuid4().hex[:8]}",
            "permissions": [Permission.USERS_READ.value, Permission.USERS_CREATE.value]
        }
        
        response = await test_client.post(
            "/api/v1/admin/roles",
            headers=headers,
            json=payload
        )
        assert response.status_code == 201
        return response.json()["id"]

    async def test_full_role_lifecycle(
        self, test_client: AsyncClient, admin_token: str, test_tenant_id: str, db_session: AsyncSession
    ):
        """Test complete CRUD lifecycle of a custom role."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # 1. Create role
        create_payload = {
            "name": f"lifecycle_role_{uuid4().hex[:8]}",
            "permissions": [Permission.USERS_READ.value]
        }
        create_response = await test_client.post(
            "/api/v1/admin/roles",
            headers=headers,
            json=create_payload
        )
        assert create_response.status_code == 201
        role_id = create_response.json()["id"]
        
        # Verify in database
        stmt = select(RoleModel).where(RoleModel.id == UUID(role_id))
        result = await db_session.execute(stmt)
        db_role = result.scalar_one_or_none()
        assert db_role is not None
        assert db_role.name == create_payload["name"]
        assert db_role.tenant_id == UUID(test_tenant_id)
        assert db_role.is_system is False
        
        # 2. Retrieve role
        get_response = await test_client.get(
            f"/api/v1/admin/roles/{role_id}",
            headers=headers
        )
        assert get_response.status_code == 200
        assert get_response.json()["name"] == create_payload["name"]
        
        # 3. Update role
        update_payload = {
            "permissions": [
                Permission.USERS_READ.value,
                Permission.USERS_CREATE.value,
                Permission.USERS_UPDATE.value
            ]
        }
        update_response = await test_client.put(
            f"/api/v1/admin/roles/{role_id}",
            headers=headers,
            json=update_payload
        )
        assert update_response.status_code == 200
        
        # Verify update in database
        await db_session.refresh(db_role)
        assert set(db_role.permissions) == set(update_payload["permissions"])
        
        # 4. Delete role
        delete_response = await test_client.delete(
            f"/api/v1/admin/roles/{role_id}",
            headers=headers
        )
        assert delete_response.status_code == 204
        
        # Verify deletion in database
        stmt = select(RoleModel).where(RoleModel.id == UUID(role_id))
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

    async def test_role_assignment_lifecycle(
        self,
        test_client: AsyncClient,
        admin_token: str,
        test_user_id: str,
        custom_role_id: str,
        db_session: AsyncSession
    ):
        """Test assigning and revoking roles from users."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # 1. Assign role
        assign_response = await test_client.post(
            f"/api/v1/admin/users/{test_user_id}/roles/{custom_role_id}",
            headers=headers
        )
        assert assign_response.status_code == 201
        assignment = assign_response.json()
        assert assignment["user_id"] == test_user_id
        assert assignment["role_id"] == custom_role_id
        
        # Verify in database
        stmt = select(UserRoleModel).where(
            UserRoleModel.user_id == UUID(test_user_id),
            UserRoleModel.role_id == UUID(custom_role_id)
        )
        result = await db_session.execute(stmt)
        db_assignment = result.scalar_one_or_none()
        assert db_assignment is not None
        assert db_assignment.assigned_by is not None
        
        # 2. Revoke role
        revoke_response = await test_client.delete(
            f"/api/v1/admin/users/{test_user_id}/roles/{custom_role_id}",
            headers=headers
        )
        assert revoke_response.status_code == 204
        
        # Verify revocation in database
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

    async def test_tenant_isolation_enforcement(
        self,
        test_client: AsyncClient,
        admin_token: str,
        other_tenant_admin_token: str,
        test_tenant_id: str,
        other_tenant_id: str,
        db_session: AsyncSession
    ):
        """Test tenant isolation in role management."""
        tenant_a_headers = {"Authorization": f"Bearer {admin_token}"}
        tenant_b_headers = {"Authorization": f"Bearer {other_tenant_admin_token}"}
        
        # Tenant A creates role
        payload_a = {
            "name": f"tenant_a_role_{uuid4().hex[:8]}",
            "permissions": [Permission.USERS_READ.value]
        }
        create_response = await test_client.post(
            "/api/v1/admin/roles",
            headers=tenant_a_headers,
            json=payload_a
        )
        assert create_response.status_code == 201
        role_a_id = create_response.json()["id"]
        
        # Tenant B tries to retrieve Tenant A's role
        get_response = await test_client.get(
            f"/api/v1/admin/roles/{role_a_id}",
            headers=tenant_b_headers
        )
        assert get_response.status_code == 404  # Tenant isolation enforced
        
        # Tenant B tries to update Tenant A's role
        update_response = await test_client.put(
            f"/api/v1/admin/roles/{role_a_id}",
            headers=tenant_b_headers,
            json={"permissions": [Permission.USERS_READ.value]}
        )
        assert update_response.status_code == 404  # Tenant isolation enforced
        
        # Tenant B tries to delete Tenant A's role
        delete_response = await test_client.delete(
            f"/api/v1/admin/roles/{role_a_id}",
            headers=tenant_b_headers
        )
        assert delete_response.status_code == 404  # Tenant isolation enforced
        
        # Verify role still exists in database
        stmt = select(RoleModel).where(RoleModel.id == UUID(role_a_id))
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is not None

    async def test_system_role_immutability(
        self, test_client: AsyncClient, admin_token: str, db_session: AsyncSession
    ):
        """Test that system roles cannot be modified or deleted."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        superadmin_role_id = str(SYSTEM_ROLE_IDS["superadmin"])
        
        # Attempt to update system role
        update_response = await test_client.put(
            f"/api/v1/admin/roles/{superadmin_role_id}",
            headers=headers,
            json={"permissions": [Permission.USERS_READ.value]}
        )
        assert update_response.status_code == 403
        
        # Attempt to delete system role
        delete_response = await test_client.delete(
            f"/api/v1/admin/roles/{superadmin_role_id}",
            headers=headers
        )
        assert delete_response.status_code == 403
        
        # Verify system role unchanged in database
        stmt = select(RoleModel).where(RoleModel.id == SYSTEM_ROLE_IDS["superadmin"])
        result = await db_session.execute(stmt)
        db_role = result.scalar_one_or_none()
        assert db_role is not None
        assert db_role.is_system is True
        assert Permission.ALL.value in db_role.permissions

    async def test_permission_validation(
        self, test_client: AsyncClient, admin_token: str
    ):
        """Test permission validation in role creation/update."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test empty permissions
        payload_empty = {
            "name": f"empty_perm_role_{uuid4().hex[:8]}",
            "permissions": []
        }
        response_empty = await test_client.post(
            "/api/v1/admin/roles",
            headers=headers,
            json=payload_empty
        )
        assert response_empty.status_code == 422
        
        # Test invalid permissions
        payload_invalid = {
            "name": f"invalid_perm_role_{uuid4().hex[:8]}",
            "permissions": ["invalid:permission"]
        }
        response_invalid = await test_client.post(
            "/api/v1/admin/roles",
            headers=headers,
            json=payload_invalid
        )
        assert response_invalid.status_code == 422
        
        # Test wildcard permission (only superadmin should set this)
        payload_wildcard = {
            "name": f"wildcard_role_{uuid4().hex[:8]}",
            "permissions": [Permission.ALL.value]
        }
        response_wildcard = await test_client.post(
            "/api/v1/admin/roles",
            headers=headers,
            json=payload_wildcard
        )
        # Should be rejected or flagged as privilege escalation
        assert response_wildcard.status_code in [403, 422]

    async def test_rbac_enforcement_non_admin(
        self, test_client: AsyncClient, user_token: str
    ):
        """Test that regular users cannot access role management."""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # List roles
        list_response = await test_client.get("/api/v1/admin/roles", headers=headers)
        assert list_response.status_code == 403
        
        # Create role
        create_response = await test_client.post(
            "/api/v1/admin/roles",
            headers=headers,
            json={"name": "test", "permissions": [Permission.USERS_READ.value]}
        )
        assert create_response.status_code == 403
        
        # Update role
        update_response = await test_client.put(
            f"/api/v1/admin/roles/{uuid4()}",
            headers=headers,
            json={"permissions": [Permission.USERS_READ.value]}
        )
        assert update_response.status_code == 403
        
        # Delete role
        delete_response = await test_client.delete(
            f"/api/v1/admin/roles/{uuid4()}",
            headers=headers
        )
        assert delete_response.status_code == 403

    async def test_duplicate_role_name_per_tenant(
        self,
        test_client: AsyncClient,
        admin_token: str,
        other_tenant_admin_token: str
    ):
        """Test duplicate role names within same tenant vs different tenants."""
        tenant_a_headers = {"Authorization": f"Bearer {admin_token}"}
        tenant_b_headers = {"Authorization": f"Bearer {other_tenant_admin_token}"}
        
        role_name = f"duplicate_test_{uuid4().hex[:8]}"
        payload = {
            "name": role_name,
            "permissions": [Permission.USERS_READ.value]
        }
        
        # Tenant A creates role
        response_a1 = await test_client.post(
            "/api/v1/admin/roles",
            headers=tenant_a_headers,
            json=payload
        )
        assert response_a1.status_code == 201
        
        # Tenant A tries to create duplicate
        response_a2 = await test_client.post(
            "/api/v1/admin/roles",
            headers=tenant_a_headers,
            json=payload
        )
        assert response_a2.status_code == 409  # Conflict
        
        # Tenant B can create role with same name (different tenant)
        response_b1 = await test_client.post(
            "/api/v1/admin/roles",
            headers=tenant_b_headers,
            json=payload
        )
        assert response_b1.status_code == 201

    async def test_role_assignment_prevents_privilege_escalation(
        self,
        test_client: AsyncClient,
        admin_token: str,
        test_user_id: str,
        db_session: AsyncSession
    ):
        """Test that tenant_admin cannot assign superadmin role."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        superadmin_role_id = str(SYSTEM_ROLE_IDS["superadmin"])
        
        # Attempt to assign superadmin role to user
        response = await test_client.post(
            f"/api/v1/admin/users/{test_user_id}/roles/{superadmin_role_id}",
            headers=headers
        )
        
        # Should be rejected (403 or 422)
        assert response.status_code in [403, 422]
        
        # Verify no assignment in database
        stmt = select(UserRoleModel).where(
            UserRoleModel.user_id == UUID(test_user_id),
            UserRoleModel.role_id == SYSTEM_ROLE_IDS["superadmin"]
        )
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

    async def test_superadmin_role_assignment_cross_tenant(
        self,
        test_client: AsyncClient,
        superadmin_token: str,
        other_tenant_user_id: str,
        custom_role_id: str,
        db_session: AsyncSession
    ):
        """Test that superadmin can assign roles across tenants."""
        headers = {"Authorization": f"Bearer {superadmin_token}"}
        
        # Superadmin assigns role to user in different tenant
        response = await test_client.post(
            f"/api/v1/admin/users/{other_tenant_user_id}/roles/{custom_role_id}",
            headers=headers
        )
        
        assert response.status_code == 201
        
        # Verify assignment in database
        stmt = select(UserRoleModel).where(
            UserRoleModel.user_id == UUID(other_tenant_user_id),
            UserRoleModel.role_id == UUID(custom_role_id)
        )
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is not None

    async def test_list_roles_pagination(
        self, test_client: AsyncClient, admin_token: str
    ):
        """Test role listing with multiple custom roles."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create 5 custom roles
        created_ids = []
        for i in range(5):
            payload = {
                "name": f"pagination_role_{i}_{uuid4().hex[:8]}",
                "permissions": [Permission.USERS_READ.value]
            }
            response = await test_client.post(
                "/api/v1/admin/roles",
                headers=headers,
                json=payload
            )
            assert response.status_code == 201
            created_ids.append(response.json()["id"])
        
        # List all roles (should include 3 system + 5 custom = 8 total)
        list_response = await test_client.get(
            "/api/v1/admin/roles",
            headers=headers
        )
        assert list_response.status_code == 200
        roles = list_response.json()
        assert len(roles) >= 8  # At least our 8 roles
        
        # Verify all created roles present
        role_ids = [r["id"] for r in roles]
        for created_id in created_ids:
            assert created_id in role_ids
