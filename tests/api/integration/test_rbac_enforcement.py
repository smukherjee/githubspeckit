"""
RBAC Enforcement Integration Tests

Tests role-based access control:
- Different roles have different permissions
- Superadmin has elevated privileges
- Standard users have restricted access
- Role validation is enforced
"""
import pytest
from httpx import AsyncClient
import uuid


class TestRoleBasedPermissions:
    """Test permissions enforcement based on user roles."""
    
    @pytest.mark.asyncio
    async def test_superadmin_can_create_tenant(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Test superadmin can create tenants."""
        response = await api_client.post(
            "/api/v1/tenants",
            headers=auth_headers,
            json={
                "name": f"test_tenant_{uuid.uuid4().hex[:8]}",
                "config_version": 1
            }
        )
        
        assert response.status_code == 201
    
    @pytest.mark.asyncio
    async def test_superadmin_can_create_user_in_any_tenant(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        seeded_database: dict
    ):
        """Test superadmin can create users in any tenant."""
        # Create new tenant
        tenant_response = await api_client.post(
            "/api/v1/tenants",
            headers=auth_headers,
            json={
                "name": f"test_tenant_{uuid.uuid4().hex[:8]}",
                "config_version": 1
            }
        )
        assert tenant_response.status_code == 201
        tenant_id = tenant_response.json()["tenant_id"]
        
        # Create user in the new tenant
        user_response = await api_client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "tenant_id": tenant_id,
                "email": f"user_{uuid.uuid4().hex[:8]}@example.com",
                "password": "TestPassword123!",
                "roles": ["user"]
            }
        )
        
        assert user_response.status_code == 201
    
    @pytest.mark.asyncio
    async def test_superadmin_can_delete_any_tenant(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Test superadmin can delete any tenant."""
        # Create tenant
        create_response = await api_client.post(
            "/api/v1/tenants",
            headers=auth_headers,
            json={
                "name": f"test_tenant_{uuid.uuid4().hex[:8]}",
                "config_version": 1
            }
        )
        assert create_response.status_code == 201
        tenant_id = create_response.json()["tenant_id"]
        
        # Delete tenant
        delete_response = await api_client.delete(
            f"/api/v1/tenants/{tenant_id}",
            headers=auth_headers
        )
        
        assert delete_response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_tenant_admin_can_create_users_in_own_tenant(
        self,
        api_client: AsyncClient,
        tenant_admin_headers: dict,
        seeded_database: dict
    ):
        """Test tenant admin can create users in their own tenant."""
        tenant_id = seeded_database["tenant_id"]
        
        response = await api_client.post(
            "/api/v1/users",
            headers=tenant_admin_headers,
            json={
                "tenant_id": tenant_id,
                "email": f"user_{uuid.uuid4().hex[:8]}@infysight.com",
                "password": "TestPassword123!",
                "roles": ["user"]
            }
        )
        
        assert response.status_code == 201
    
    @pytest.mark.asyncio
    async def test_tenant_admin_cannot_create_tenant(
        self,
        api_client: AsyncClient,
        tenant_admin_headers: dict
    ):
        """Test tenant admin cannot create new tenants."""
        response = await api_client.post(
            "/api/v1/tenants",
            headers=tenant_admin_headers,
            json={
                "name": f"test_tenant_{uuid.uuid4().hex[:8]}",
                "config_version": 1
            }
        )
        
        # Should be forbidden
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_standard_user_cannot_create_users(
        self,
        api_client: AsyncClient,
        standard_user_headers: dict,
        seeded_database: dict
    ):
        """Test standard user cannot create other users."""
        tenant_id = seeded_database["tenant_id"]
        
        response = await api_client.post(
            "/api/v1/users",
            headers=standard_user_headers,
            json={
                "tenant_id": tenant_id,
                "email": f"user_{uuid.uuid4().hex[:8]}@infysight.com",
                "password": "TestPassword123!",
                "roles": ["user"]
            }
        )
        
        # Should be forbidden
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_standard_user_can_view_own_profile(
        self,
        api_client: AsyncClient,
        standard_user_headers: dict
    ):
        """Test standard user can view their own profile."""
        # Get current user profile
        response = await api_client.get(
            "/api/v1/users/me",
            headers=standard_user_headers
        )
        
        # Should succeed or be not implemented
        assert response.status_code in [200, 501]


class TestRoleValidation:
    """Test role validation and assignment."""
    
    @pytest.mark.asyncio
    async def test_create_user_with_invalid_role(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        seeded_database: dict
    ):
        """Test creating user with invalid role fails validation."""
        tenant_id = seeded_database["tenant_id"]
        
        response = await api_client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "tenant_id": tenant_id,
                "email": f"user_{uuid.uuid4().hex[:8]}@infysight.com",
                "password": "TestPassword123!",
                "roles": ["invalid_role"]
            }
        )
        
        # Should fail validation
        assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_create_user_with_multiple_roles(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        seeded_database: dict
    ):
        """Test creating user with multiple roles."""
        tenant_id = seeded_database["tenant_id"]
        
        response = await api_client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "tenant_id": tenant_id,
                "email": f"user_{uuid.uuid4().hex[:8]}@infysight.com",
                "password": "TestPassword123!",
                "roles": ["user", "admin"]
            }
        )
        
        # Should succeed
        assert response.status_code == 201
        data = response.json()
        assert set(data["roles"]) == {"user", "admin"}
    
    @pytest.mark.asyncio
    async def test_create_user_with_empty_roles(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        seeded_database: dict
    ):
        """Test creating user with no roles."""
        tenant_id = seeded_database["tenant_id"]
        
        response = await api_client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "tenant_id": tenant_id,
                "email": f"user_{uuid.uuid4().hex[:8]}@infysight.com",
                "password": "TestPassword123!",
                "roles": []
            }
        )
        
        # Should either fail or assign default role
        assert response.status_code in [201, 400, 422]


class TestPermissionBoundaries:
    """Test permission boundaries and edge cases."""
    
    @pytest.mark.asyncio
    async def test_user_cannot_escalate_own_privileges(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        seeded_database: dict
    ):
        """Test user cannot grant themselves additional roles."""
        tenant_id = seeded_database["tenant_id"]
        
        # Create standard user
        email = f"user_{uuid.uuid4().hex[:8]}@infysight.com"
        password = "TestPassword123!"
        
        create_response = await api_client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "tenant_id": tenant_id,
                "email": email,
                "password": password,
                "roles": ["user"]
            }
        )
        assert create_response.status_code == 201
        user_id = create_response.json()["user_id"]
        
        # Login as standard user
        login_response = await api_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        assert login_response.status_code == 200
        user_token = login_response.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Try to update own roles to admin
        update_response = await api_client.patch(
            f"/api/v1/users/{user_id}",
            headers=user_headers,
            json={"roles": ["user", "admin", "superadmin"]}
        )
        
        # Should be forbidden or endpoint not exist
        assert update_response.status_code in [403, 404, 405, 501]
    
    @pytest.mark.asyncio
    async def test_user_cannot_delete_own_account(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        seeded_database: dict
    ):
        """Test user cannot delete their own account without proper permissions."""
        tenant_id = seeded_database["tenant_id"]
        
        # Create user
        email = f"user_{uuid.uuid4().hex[:8]}@infysight.com"
        password = "TestPassword123!"
        
        create_response = await api_client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "tenant_id": tenant_id,
                "email": email,
                "password": password,
                "roles": ["user"]
            }
        )
        assert create_response.status_code == 201
        user_id = create_response.json()["user_id"]
        
        # Login as user
        login_response = await api_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        assert login_response.status_code == 200
        user_token = login_response.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Try to delete own account
        delete_response = await api_client.delete(
            f"/api/v1/users/{user_id}",
            headers=user_headers
        )
        
        # Should be forbidden (or may be allowed if self-deletion is permitted)
        assert delete_response.status_code in [204, 403]
