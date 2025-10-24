"""
Contract tests for role management endpoints (FR-122 V1.0).

Tests role CRUD operations, system role immutability, tenant isolation,
and permission-based RBAC. Uses httpx.AsyncClient against running API.
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4

from src.domain.roles.permissions import Permission


@pytest.mark.asyncio
class TestRoleManagementContract:
    """Contract tests for /api/v1/admin/roles endpoints."""

    @pytest.fixture
    async def admin_headers(self, test_client: AsyncClient, admin_token: str):
        """Headers with admin authentication."""
        return {"Authorization": f"Bearer {admin_token}"}

    @pytest.fixture
    async def superadmin_headers(self, test_client: AsyncClient, superadmin_token: str):
        """Headers with superadmin authentication."""
        return {"Authorization": f"Bearer {superadmin_token}"}

    async def test_list_roles_includes_system_roles(
        self, test_client: AsyncClient, admin_headers: dict
    ):
        """FR-122: List roles should return system roles by default."""
        response = await test_client.get(
            "/api/v1/admin/roles",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        roles = response.json()
        assert isinstance(roles, list)
        
        # Should include 3 system roles
        system_roles = [r for r in roles if r["is_system"]]
        assert len(system_roles) == 3
        
        role_names = {r["name"] for r in system_roles}
        assert role_names == {"superadmin", "tenant_admin", "user"}

    async def test_list_roles_exclude_system_roles(
        self, test_client: AsyncClient, admin_headers: dict
    ):
        """FR-122: List roles can exclude system roles."""
        response = await test_client.get(
            "/api/v1/admin/roles?include_system=false",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        roles = response.json()
        
        # Should not include any system roles
        system_roles = [r for r in roles if r["is_system"]]
        assert len(system_roles) == 0

    async def test_create_custom_role_success(
        self, test_client: AsyncClient, admin_headers: dict, test_tenant_id: str
    ):
        """FR-122: tenant_admin can create custom roles for their tenant."""
        payload = {
            "name": f"custom_role_{uuid4().hex[:8]}",
            "permissions": [
                Permission.USERS_READ.value,
                Permission.USERS_CREATE.value
            ]
        }
        
        response = await test_client.post(
            "/api/v1/admin/roles",
            headers=admin_headers,
            json=payload
        )
        
        assert response.status_code == 201
        role = response.json()
        
        assert role["name"] == payload["name"]
        assert role["is_system"] is False
        assert role["tenant_id"] == test_tenant_id
        assert set(role["permissions"]) == set(payload["permissions"])

    async def test_create_system_role_rejected(
        self, test_client: AsyncClient, admin_headers: dict
    ):
        """FR-122: Cannot create system roles via API (rejected via privilege escalation check)."""
        payload = {
            "name": "new_system_role",
            "permissions": [Permission.ALL.value],
            "is_system": True  # This field is ignored by API (not in schema)
        }
        
        response = await test_client.post(
            "/api/v1/admin/roles",
            headers=admin_headers,
            json=payload
        )
        
        # Should reject due to superadmin permissions (403)
        assert response.status_code == 403
        # Accept either "system role" or "superadmin" in error message
        detail = response.json()["detail"].lower()
        assert "system" in detail or "superadmin" in detail

    async def test_create_role_duplicate_name_rejected(
        self, test_client: AsyncClient, admin_headers: dict, test_tenant_id: str
    ):
        """FR-122: Cannot create roles with duplicate names in same tenant."""
        role_name = f"duplicate_test_{uuid4().hex[:8]}"
        payload = {
            "name": role_name,
            "permissions": [Permission.USERS_READ.value]
        }
        
        # Create first role
        response1 = await test_client.post(
            "/api/v1/admin/roles",
            headers=admin_headers,
            json=payload
        )
        assert response1.status_code == 201
        
        # Attempt to create duplicate
        response2 = await test_client.post(
            "/api/v1/admin/roles",
            headers=admin_headers,
            json=payload
        )
        
        assert response2.status_code == 409
        assert "already exists" in response2.json()["detail"].lower()

    async def test_get_role_by_id_success(
        self, test_client: AsyncClient, admin_headers: dict
    ):
        """FR-122: Retrieve role details by ID."""
        # First create a role
        payload = {
            "name": f"test_role_{uuid4().hex[:8]}",
            "permissions": [Permission.USERS_READ.value]
        }
        create_response = await test_client.post(
            "/api/v1/admin/roles",
            headers=admin_headers,
            json=payload
        )
        assert create_response.status_code == 201
        role_id = create_response.json()["id"]
        
        # Retrieve by ID
        response = await test_client.get(
            f"/api/v1/admin/roles/{role_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        role = response.json()
        assert role["id"] == role_id
        assert role["name"] == payload["name"]

    async def test_get_role_not_found(
        self, test_client: AsyncClient, admin_headers: dict
    ):
        """FR-122: Return 404 for non-existent role."""
        fake_id = str(uuid4())
        response = await test_client.get(
            f"/api/v1/admin/roles/{fake_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_update_custom_role_success(
        self, test_client: AsyncClient, admin_headers: dict
    ):
        """FR-122: Update custom role permissions."""
        # Create role
        create_payload = {
            "name": f"updatable_role_{uuid4().hex[:8]}",
            "permissions": [Permission.USERS_READ.value]
        }
        create_response = await test_client.post(
            "/api/v1/admin/roles",
            headers=admin_headers,
            json=create_payload
        )
        assert create_response.status_code == 201
        role_id = create_response.json()["id"]
        
        # Update permissions
        update_payload = {
            "permissions": [
                Permission.USERS_READ.value,
                Permission.USERS_CREATE.value,
                Permission.USERS_UPDATE.value
            ]
        }
        response = await test_client.put(
            f"/api/v1/admin/roles/{role_id}",
            headers=admin_headers,
            json=update_payload
        )
        
        assert response.status_code == 200
        role = response.json()
        assert set(role["permissions"]) == set(update_payload["permissions"])

    async def test_update_system_role_rejected(
        self, test_client: AsyncClient, admin_headers: dict
    ):
        """FR-122: Cannot update system roles."""
        # Get superadmin role ID (system role)
        list_response = await test_client.get(
            "/api/v1/admin/roles",
            headers=admin_headers
        )
        roles = list_response.json()
        superadmin_role = next(r for r in roles if r["name"] == "superadmin")
        
        # Attempt to update
        update_payload = {
            "permissions": [Permission.USERS_READ.value]  # Try to remove permissions
        }
        response = await test_client.put(
            f"/api/v1/admin/roles/{superadmin_role['id']}",
            headers=admin_headers,
            json=update_payload
        )
        
        assert response.status_code in [400, 403]
        assert "system role" in response.json()["detail"].lower()

    async def test_delete_custom_role_success(
        self, test_client: AsyncClient, admin_headers: dict
    ):
        """FR-122: Delete custom role."""
        # Create role
        create_payload = {
            "name": f"deletable_role_{uuid4().hex[:8]}",
            "permissions": [Permission.USERS_READ.value]
        }
        create_response = await test_client.post(
            "/api/v1/admin/roles",
            headers=admin_headers,
            json=create_payload
        )
        assert create_response.status_code == 201
        role_id = create_response.json()["id"]
        
        # Delete
        response = await test_client.delete(
            f"/api/v1/admin/roles/{role_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 204
        
        # Verify deletion
        get_response = await test_client.get(
            f"/api/v1/admin/roles/{role_id}",
            headers=admin_headers
        )
        assert get_response.status_code == 404

    async def test_delete_system_role_rejected(
        self, test_client: AsyncClient, admin_headers: dict
    ):
        """FR-122: Cannot delete system roles."""
        # Get user role ID (system role)
        list_response = await test_client.get(
            "/api/v1/admin/roles",
            headers=admin_headers
        )
        roles = list_response.json()
        user_role = next(r for r in roles if r["name"] == "user")
        
        # Attempt to delete
        response = await test_client.delete(
            f"/api/v1/admin/roles/{user_role['id']}",
            headers=admin_headers
        )
        
        assert response.status_code in [400, 403]
        assert "system role" in response.json()["detail"].lower()

    async def test_assign_role_to_user_success(
        self, test_client: AsyncClient, admin_headers: dict, test_user_id: str
    ):
        """FR-122: Assign custom role to user."""
        # Create custom role
        create_payload = {
            "name": f"assignable_role_{uuid4().hex[:8]}",
            "permissions": [Permission.USERS_READ.value]
        }
        create_response = await test_client.post(
            "/api/v1/admin/roles",
            headers=admin_headers,
            json=create_payload
        )
        assert create_response.status_code == 201
        role_id = create_response.json()["id"]
        
        # Assign to user
        response = await test_client.post(
            f"/api/v1/admin/users/{test_user_id}/roles/{role_id}",
            headers=admin_headers
        )
        
        # Idempotent operation returns 200 OK
        assert response.status_code == 200
        assignment = response.json()
        assert assignment["user_id"] == test_user_id
        assert assignment["role_id"] == role_id
        assert "message" in assignment

    async def test_revoke_role_from_user_success(
        self, test_client: AsyncClient, admin_headers: dict, test_user_id: str
    ):
        """FR-122: Revoke role from user."""
        # Create and assign role
        create_payload = {
            "name": f"revokable_role_{uuid4().hex[:8]}",
            "permissions": [Permission.USERS_READ.value]
        }
        create_response = await test_client.post(
            "/api/v1/admin/roles",
            headers=admin_headers,
            json=create_payload
        )
        role_id = create_response.json()["id"]
        
        assign_response = await test_client.post(
            f"/api/v1/admin/users/{test_user_id}/roles/{role_id}",
            headers=admin_headers
        )
        assert assign_response.status_code == 200
        
        # Revoke
        response = await test_client.delete(
            f"/api/v1/admin/users/{test_user_id}/roles/{role_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 204

    @pytest.mark.skip(reason="Requires other_tenant_admin_headers fixture - not yet implemented")
    async def test_tenant_isolation_role_creation(
        self, test_client: AsyncClient, admin_headers: dict, other_tenant_admin_headers: dict
    ):
        """FR-122: tenant_admin cannot see other tenant's custom roles."""
        # Tenant A creates role
        payload_a = {
            "name": f"tenant_a_role_{uuid4().hex[:8]}",
            "permissions": [Permission.USERS_READ.value]
        }
        create_response = await test_client.post(
            "/api/v1/admin/roles",
            headers=admin_headers,
            json=payload_a
        )
        assert create_response.status_code == 201
        role_a_id = create_response.json()["id"]
        
        # Tenant B lists roles - should not see Tenant A's custom role
        list_response = await test_client.get(
            "/api/v1/admin/roles?include_system=false",
            headers=other_tenant_admin_headers
        )
        
        roles = list_response.json()
        role_ids = [r["id"] for r in roles]
        assert role_a_id not in role_ids

    async def test_superadmin_sees_all_roles(
        self, test_client: AsyncClient, superadmin_headers: dict, admin_headers: dict
    ):
        """FR-122: superadmin can see all tenant custom roles."""
        # Tenant admin creates role
        payload = {
            "name": f"tenant_specific_role_{uuid4().hex[:8]}",
            "permissions": [Permission.USERS_READ.value]
        }
        create_response = await test_client.post(
            "/api/v1/admin/roles",
            headers=admin_headers,
            json=payload
        )
        assert create_response.status_code == 201
        role_id = create_response.json()["id"]
        
        # Superadmin lists all roles
        list_response = await test_client.get(
            "/api/v1/admin/roles",
            headers=superadmin_headers
        )
        
        roles = list_response.json()
        role_ids = [r["id"] for r in roles]
        assert role_id in role_ids

    async def test_regular_user_cannot_access_roles(
        self, test_client: AsyncClient, regular_user_token: str
    ):
        """FR-122: Regular users (non-admin) cannot access role management."""
        headers = {"Authorization": f"Bearer {regular_user_token}"}
        
        # Attempt to list roles
        response = await test_client.get(
            "/api/v1/admin/roles",
            headers=headers
        )
        
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()

    async def test_invalid_permission_rejected(
        self, test_client: AsyncClient, admin_headers: dict
    ):
        """FR-122: Invalid permission strings are rejected."""
        payload = {
            "name": f"invalid_perm_role_{uuid4().hex[:8]}",
            "permissions": ["invalid:permission", "not:real"]
        }
        
        response = await test_client.post(
            "/api/v1/admin/roles",
            headers=admin_headers,
            json=payload
        )
        
        # Application-level validation returns 400 (not 422 which is for schema validation)
        assert response.status_code == 400
        assert "permission" in response.json()["detail"].lower()
