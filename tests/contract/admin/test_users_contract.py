"""
Contract tests for admin user endpoints.
Tests API shape, request/response schemas, and status codes.
These tests MUST FAIL until implementation is complete.
"""
import pytest
from httpx import AsyncClient
from fastapi import status


class TestAdminUserContracts:
    """Contract tests for /api/v1/admin/users endpoints."""

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_list_users_contract(self, client: AsyncClient, superadmin_headers):
        """Test GET /api/v1/admin/users contract."""
        response = await client.get("/api/v1/admin/users", headers=superadmin_headers)
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)
        
        # Pagination structure
        pagination = data["pagination"]
        assert "page" in pagination
        assert "per_page" in pagination
        assert "total" in pagination
        assert "total_pages" in pagination
        
        # If data exists, validate user structure
        if data["data"]:
            user = data["data"][0]
            required_fields = [
                "user_id", "tenant_id", "email", "is_disabled",
                "failed_login_attempts", "roles", "created_at",
                "updated_at", "created_by", "updated_by"
            ]
            for field in required_fields:
                assert field in user
            
            # Roles should be array
            assert isinstance(user["roles"], list)

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_list_users_with_tenant_filter_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test GET /api/v1/admin/users with tenant_id filter."""
        response = await client.get(
            "/api/v1/admin/users",
            headers=superadmin_headers,
            params={"tenant_id": test_tenant_id}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # All users should belong to the filtered tenant
        for user in data["data"]:
            assert user["tenant_id"] == test_tenant_id

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_list_users_with_filters_contract(self, client: AsyncClient, superadmin_headers):
        """Test GET /api/v1/admin/users with various filters."""
        params = {
            "page": 1,
            "per_page": 5,
            "sort": "email",
            "order": "asc",
            "role": "tenant_admin",
            "is_disabled": False
        }
        
        response = await client.get(
            "/api/v1/admin/users",
            headers=superadmin_headers,
            params=params
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 5

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_create_user_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test POST /api/v1/admin/users contract."""
        user_data = {
            "email": "contract.test@example.com",
            "full_name": "Contract Test User",
            "job_title": "Software Engineer",
            "department": "Engineering",
            "phone": "+1-555-0123",
            "timezone": "America/New_York",
            "language": "en",
            "roles": ["user"],
            "is_disabled": False,
            "password": "SecurePassword123!"
        }
        
        response = await client.post(
            "/api/v1/admin/users",
            headers=superadmin_headers,
            params={"tenant_id": test_tenant_id},
            json=user_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        assert "data" in data
        user = data["data"]
        
        # Required fields
        assert "user_id" in user
        assert "tenant_id" in user
        assert user["tenant_id"] == test_tenant_id
        assert user["email"] == user_data["email"]
        assert user["full_name"] == user_data["full_name"]
        assert user["roles"] == user_data["roles"]
        assert user["is_disabled"] == user_data["is_disabled"]
        
        # Password should not be returned
        assert "password" not in user
        assert "password_hash" not in user

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_create_user_without_password_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test POST /api/v1/admin/users without password (invitation flow)."""
        user_data = {
            "email": "invitation.test@example.com",
            "full_name": "Invitation Test User",
            "roles": ["user"],
            "is_disabled": False
        }
        
        response = await client.post(
            "/api/v1/admin/users",
            headers=superadmin_headers,
            params={"tenant_id": test_tenant_id},
            json=user_data
        )
        
        # Should create user and send invitation
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        user = data["data"]
        assert user["email"] == user_data["email"]

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_create_user_validation_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test POST /api/v1/admin/users validation contract."""
        # Missing required fields
        invalid_data = {"full_name": "Incomplete User"}
        
        response = await client.post(
            "/api/v1/admin/users",
            headers=superadmin_headers,
            params={"tenant_id": test_tenant_id},
            json=invalid_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_get_user_by_id_contract(self, client: AsyncClient, superadmin_headers, test_user_id):
        """Test GET /api/v1/admin/users/{user_id} contract."""
        response = await client.get(
            f"/api/v1/admin/users/{test_user_id}",
            headers=superadmin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "data" in data
        user = data["data"]
        assert user["user_id"] == test_user_id

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_get_user_not_found_contract(self, client: AsyncClient, superadmin_headers):
        """Test GET /api/v1/admin/users/{user_id} not found contract."""
        fake_user_id = "00000000-0000-0000-0000-000000000000"
        
        response = await client.get(
            f"/api/v1/admin/users/{fake_user_id}",
            headers=superadmin_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_update_user_contract(self, client: AsyncClient, superadmin_headers, test_user_id):
        """Test PUT /api/v1/admin/users/{user_id} contract."""
        update_data = {
            "full_name": "Updated Test User",
            "job_title": "Senior Engineer",
            "timezone": "UTC",
            "language": "es",
            "is_disabled": True
        }
        
        response = await client.put(
            f"/api/v1/admin/users/{test_user_id}",
            headers=superadmin_headers,
            json=update_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "data" in data
        user = data["data"]
        assert user["full_name"] == update_data["full_name"]
        assert user["job_title"] == update_data["job_title"]
        assert user["is_disabled"] == update_data["is_disabled"]

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_delete_user_contract(self, client: AsyncClient, superadmin_headers, test_user_id):
        """Test DELETE /api/v1/admin/users/{user_id} contract."""
        response = await client.delete(
            f"/api/v1/admin/users/{test_user_id}",
            headers=superadmin_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not response.content

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_tenant_admin_list_users_scoped_contract(self, client: AsyncClient, tenant_admin_headers):
        """Test that tenant_admin can only see users in their tenant."""
        response = await client.get("/api/v1/admin/users", headers=tenant_admin_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # All users should belong to the same tenant
        if data["data"]:
            tenant_id = data["data"][0]["tenant_id"]
            for user in data["data"]:
                assert user["tenant_id"] == tenant_id

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_tenant_admin_cross_tenant_user_forbidden_contract(
        self, client: AsyncClient, tenant_admin_headers
    ):
        """Test that tenant_admin cannot access users from other tenants."""
        # Try to create user with different tenant_id
        other_tenant_id = "11111111-1111-1111-1111-111111111111"
        user_data = {
            "email": "unauthorized@example.com",
            "roles": ["user"],
            "is_disabled": False
        }
        
        response = await client.post(
            "/api/v1/admin/users",
            headers=tenant_admin_headers,
            params={"tenant_id": other_tenant_id},
            json=user_data
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_standard_user_access_forbidden_contract(self, client: AsyncClient, user_headers):
        """Test that standard users cannot access admin user endpoints."""
        response = await client.get("/api/v1/admin/users", headers=user_headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "error" in data

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_unauthenticated_access_contract(self, client: AsyncClient):
        """Test that unauthenticated requests are rejected."""
        response = await client.get("/api/v1/admin/users")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED