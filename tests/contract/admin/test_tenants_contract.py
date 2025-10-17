"""
Contract tests for admin tenant endpoints.
Tests API shape, request/response schemas, and status codes.
These tests MUST FAIL until implementation is complete.
"""
import pytest
from httpx import AsyncClient
from fastapi import status


class TestAdminTenantContracts:
    """Contract tests for /api/v1/admin/tenants endpoints."""

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_list_tenants_contract(self, client: AsyncClient, superadmin_headers):
        """Test GET /api/v1/admin/tenants contract."""
        response = await client.get("/api/v1/admin/tenants", headers=superadmin_headers)
        
        # Expected status
        assert response.status_code == status.HTTP_200_OK
        
        # Expected response structure
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
        
        # If data exists, validate tenant structure
        if data["data"]:
            tenant = data["data"][0]
            assert "tenant_id" in tenant
            assert "name" in tenant
            assert "is_active" in tenant
            assert "created_at" in tenant
            assert "updated_at" in tenant
            assert "created_by" in tenant
            assert "updated_by" in tenant

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_list_tenants_query_params_contract(self, client: AsyncClient, superadmin_headers):
        """Test GET /api/v1/admin/tenants with query parameters."""
        response = await client.get(
            "/api/v1/admin/tenants",
            headers=superadmin_headers,
            params={"page": 1, "per_page": 10, "sort": "name", "order": "asc"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 10

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_create_tenant_contract(self, client: AsyncClient, superadmin_headers):
        """Test POST /api/v1/admin/tenants contract."""
        tenant_data = {
            "name": "Contract Test Tenant",
            "is_active": True,
            "settings": {
                "max_users": 100,
                "features": ["analytics", "reporting"],
                "branding": {
                    "logo_url": "https://example.com/logo.png",
                    "primary_color": "#FF5733",
                    "secondary_color": "#33FF57"
                }
            }
        }
        
        response = await client.post(
            "/api/v1/admin/tenants",
            headers=superadmin_headers,
            json=tenant_data
        )
        
        # Expected status
        assert response.status_code == status.HTTP_201_CREATED
        
        # Expected response structure
        data = response.json()
        assert "data" in data
        tenant = data["data"]
        
        # Required fields
        assert "tenant_id" in tenant
        assert "name" in tenant
        assert tenant["name"] == tenant_data["name"]
        assert "is_active" in tenant
        assert tenant["is_active"] == tenant_data["is_active"]
        assert "settings" in tenant
        assert "created_at" in tenant
        assert "updated_at" in tenant
        assert "created_by" in tenant
        assert "updated_by" in tenant

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_create_tenant_validation_contract(self, client: AsyncClient, superadmin_headers):
        """Test POST /api/v1/admin/tenants validation contract."""
        # Missing required field
        invalid_data = {"is_active": True}
        
        response = await client.post(
            "/api/v1/admin/tenants",
            headers=superadmin_headers,
            json=invalid_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_get_tenant_by_id_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test GET /api/v1/admin/tenants/{tenant_id} contract."""
        response = await client.get(
            f"/api/v1/admin/tenants/{test_tenant_id}",
            headers=superadmin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "data" in data
        tenant = data["data"]
        assert tenant["tenant_id"] == test_tenant_id

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_get_tenant_not_found_contract(self, client: AsyncClient, superadmin_headers):
        """Test GET /api/v1/admin/tenants/{tenant_id} not found contract."""
        fake_tenant_id = "00000000-0000-0000-0000-000000000000"
        
        response = await client.get(
            f"/api/v1/admin/tenants/{fake_tenant_id}",
            headers=superadmin_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert "message" in data["error"]

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_update_tenant_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test PUT /api/v1/admin/tenants/{tenant_id} contract."""
        update_data = {
            "name": "Updated Contract Test Tenant",
            "is_active": False,
            "settings": {"max_users": 200}
        }
        
        response = await client.put(
            f"/api/v1/admin/tenants/{test_tenant_id}",
            headers=superadmin_headers,
            json=update_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "data" in data
        tenant = data["data"]
        assert tenant["name"] == update_data["name"]
        assert tenant["is_active"] == update_data["is_active"]

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_delete_tenant_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test DELETE /api/v1/admin/tenants/{tenant_id} contract."""
        response = await client.delete(
            f"/api/v1/admin/tenants/{test_tenant_id}",
            headers=superadmin_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not response.content

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_tenant_admin_list_tenants_forbidden_contract(self, client: AsyncClient, tenant_admin_headers):
        """Test that tenant_admin cannot list all tenants."""
        response = await client.get("/api/v1/admin/tenants", headers=tenant_admin_headers)
        
        # Tenant admin should only see their own tenant or get 403
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # Should only see one tenant (their own)
            assert len(data["data"]) == 1

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_tenant_admin_create_tenant_forbidden_contract(self, client: AsyncClient, tenant_admin_headers):
        """Test that tenant_admin cannot create tenants."""
        tenant_data = {"name": "Unauthorized Tenant", "is_active": True}
        
        response = await client.post(
            "/api/v1/admin/tenants",
            headers=tenant_admin_headers,
            json=tenant_data
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "error" in data

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_unauthenticated_access_contract(self, client: AsyncClient):
        """Test that unauthenticated requests are rejected."""
        response = await client.get("/api/v1/admin/tenants")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data