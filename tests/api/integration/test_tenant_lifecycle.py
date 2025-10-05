"""
Tenant Management Integration Tests

Tests tenant lifecycle operations:
- List tenants
- Create new tenant
- Soft delete tenant
- Restore tenant
- RBAC enforcement for tenant operations
"""
import pytest
from httpx import AsyncClient
import uuid


class TestTenantLifecycle:
    """Test tenant CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_list_tenants(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Test listing all tenants."""
        response = await api_client.get(
            "/api/v1/tenants",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Handle both list and dict formats
        if isinstance(data, dict) and "tenants" in data:
            tenants = data["tenants"]
        else:
            tenants = data
        assert isinstance(tenants, list)
        assert len(tenants) >= 1  # At least infysight tenant
        
        # Verify infysight tenant exists
        tenant_names = [t["name"] for t in tenants]
        assert "infysight" in tenant_names
    
    @pytest.mark.asyncio
    async def test_create_tenant(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Test creating a new tenant."""
        tenant_name = f"test_tenant_{uuid.uuid4().hex[:8]}"
        
        response = await api_client.post(
            "/api/v1/tenants",
            headers=auth_headers,
            json={
                "name": tenant_name,
                "config_version": 1
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert data["name"] == tenant_name
        assert "tenant_id" in data
        assert data["status"] == "active"
        assert data["config_version"] == 1
        assert "created_at" in data
        assert "updated_at" in data
    
    @pytest.mark.asyncio
    async def test_create_duplicate_tenant_fails(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Test creating tenant with duplicate name fails."""
        tenant_name = f"test_tenant_{uuid.uuid4().hex[:8]}"
        
        # Create first tenant
        response1 = await api_client.post(
            "/api/v1/tenants",
            headers=auth_headers,
            json={"name": tenant_name, "config_version": 1}
        )
        assert response1.status_code == 201
        
        # Try to create duplicate
        response2 = await api_client.post(
            "/api/v1/tenants",
            headers=auth_headers,
            json={"name": tenant_name, "config_version": 1}
        )
        
        # Should fail with 409 Conflict
        assert response2.status_code == 409
    
    @pytest.mark.asyncio
    async def test_soft_delete_tenant(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Test soft deleting a tenant."""
        # Create tenant first
        tenant_name = f"test_tenant_{uuid.uuid4().hex[:8]}"
        create_response = await api_client.post(
            "/api/v1/tenants",
            headers=auth_headers,
            json={"name": tenant_name, "config_version": 1}
        )
        assert create_response.status_code == 201
        tenant_id = create_response.json()["tenant_id"]
        
        # Soft delete tenant
        delete_response = await api_client.delete(
            f"/api/v1/tenants/{tenant_id}",
            headers=auth_headers
        )
        
        assert delete_response.status_code == 204
        
        # Verify tenant is soft deleted (list should not include it)
        list_response = await api_client.get(
            "/api/v1/tenants",
            headers=auth_headers
        )
        assert list_response.status_code == 200
        tenants_data = list_response.json()
        tenants = tenants_data.get("tenants", tenants_data) if isinstance(tenants_data, dict) else tenants_data
        tenant_ids = [t["tenant_id"] for t in tenants]
        assert tenant_id not in tenant_ids
    
    @pytest.mark.asyncio
    async def test_restore_tenant(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Test restoring a soft-deleted tenant."""
        # Create and soft delete tenant
        tenant_name = f"test_tenant_{uuid.uuid4().hex[:8]}"
        create_response = await api_client.post(
            "/api/v1/tenants",
            headers=auth_headers,
            json={"name": tenant_name, "config_version": 1}
        )
        assert create_response.status_code == 201
        tenant_id = create_response.json()["tenant_id"]
        
        delete_response = await api_client.delete(
            f"/api/v1/tenants/{tenant_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 204
        
        # Restore tenant
        restore_response = await api_client.post(
            f"/api/v1/tenants/{tenant_id}/restore",
            headers=auth_headers
        )
        
        assert restore_response.status_code == 200
        
        # Verify tenant is restored
        list_response = await api_client.get(
            "/api/v1/tenants",
            headers=auth_headers
        )
        assert list_response.status_code == 200
        tenants_data = list_response.json()
        tenants = tenants_data.get("tenants", tenants_data) if isinstance(tenants_data, dict) else tenants_data
        tenant_ids = [t["tenant_id"] for t in tenants]
        assert tenant_id in tenant_ids


class TestTenantAccessControl:
    """Test RBAC enforcement for tenant operations."""
    
    @pytest.mark.asyncio
    async def test_list_tenants_requires_authentication(
        self,
        api_client: AsyncClient
    ):
        """Test listing tenants requires authentication."""
        response = await api_client.get("/api/v1/tenants")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_create_tenant_requires_authentication(
        self,
        api_client: AsyncClient
    ):
        """Test creating tenant requires authentication."""
        response = await api_client.post(
            "/api/v1/tenants",
            json={"name": "test_tenant", "config_version": 1}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_delete_tenant_requires_authentication(
        self,
        api_client: AsyncClient
    ):
        """Test deleting tenant requires authentication."""
        fake_tenant_id = str(uuid.uuid4())
        response = await api_client.delete(
            f"/api/v1/tenants/{fake_tenant_id}"
        )
        
        assert response.status_code == 401


class TestTenantValidation:
    """Test tenant input validation."""
    
    @pytest.mark.asyncio
    async def test_create_tenant_with_empty_name(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Test creating tenant with empty name fails."""
        response = await api_client.post(
            "/api/v1/tenants",
            headers=auth_headers,
            json={"name": "", "config_version": 1}
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_tenant_with_missing_config_version(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Test creating tenant without config_version."""
        tenant_name = f"test_tenant_{uuid.uuid4().hex[:8]}"
        response = await api_client.post(
            "/api/v1/tenants",
            headers=auth_headers,
            json={"name": tenant_name}
        )
        
        # Should use default config_version=1 and succeed
        assert response.status_code == 201
        data = response.json()
        assert data["config_version"] == 1
    
    @pytest.mark.asyncio
    async def test_create_tenant_with_invalid_uuid(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Test creating tenant with invalid UUID fails."""
        response = await api_client.post(
            "/api/v1/tenants",
            headers=auth_headers,
            json={
                "tenant_id": "not-a-uuid",
                "name": "test_tenant",
                "config_version": 1
            }
        )
        
        assert response.status_code == 422
