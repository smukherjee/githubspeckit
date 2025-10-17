"""
Contract tests for admin feature flag endpoints.
Tests API shape, request/response schemas, and status codes.
These tests MUST FAIL until implementation is complete.
"""
import pytest
from httpx import AsyncClient
from fastapi import status


class TestAdminFeatureFlagContracts:
    """Contract tests for /api/v1/admin/feature-flags endpoints."""

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_list_feature_flags_contract(self, client: AsyncClient, superadmin_headers):
        """Test GET /api/v1/admin/feature-flags contract."""
        response = await client.get("/api/v1/admin/feature-flags", headers=superadmin_headers)
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)
        
        # If data exists, validate feature flag structure
        if data["data"]:
            flag = data["data"][0]
            required_fields = [
                "flag_id", "tenant_id", "flag_key", "flag_name", "description",
                "flag_type", "default_value", "is_enabled", "conditions",
                "created_at", "updated_at", "created_by", "updated_by"
            ]
            for field in required_fields:
                assert field in flag
            
            # Validate enums and types
            assert flag["flag_type"] in ["BOOLEAN", "STRING", "INTEGER", "JSON"]
            assert isinstance(flag["is_enabled"], bool)
            assert isinstance(flag["conditions"], dict) or flag["conditions"] is None

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_list_feature_flags_with_filters_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test GET /api/v1/admin/feature-flags with filters."""
        params = {
            "tenant_id": test_tenant_id,
            "flag_type": "BOOLEAN",
            "is_enabled": True,
            "page": 1,
            "per_page": 10
        }
        
        response = await client.get(
            "/api/v1/admin/feature-flags",
            headers=superadmin_headers,
            params=params
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # All flags should match filters
        for flag in data["data"]:
            if params["tenant_id"]:
                assert flag["tenant_id"] == test_tenant_id
            assert flag["flag_type"] == "BOOLEAN"
            assert flag["is_enabled"] is True

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_create_boolean_feature_flag_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test POST /api/v1/admin/feature-flags with boolean flag."""
        flag_data = {
            "flag_key": "contract_test_boolean_flag",
            "flag_name": "Contract Test Boolean Feature",
            "description": "Boolean feature flag for contract testing",
            "flag_type": "BOOLEAN",
            "default_value": True,
            "is_enabled": True,
            "conditions": {
                "user_roles": ["tenant_admin"],
                "user_attributes": {
                    "subscription_tier": "premium"
                },
                "rollout_percentage": 50
            }
        }
        
        response = await client.post(
            "/api/v1/admin/feature-flags",
            headers=superadmin_headers,
            params={"tenant_id": test_tenant_id},
            json=flag_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        assert "data" in data
        flag = data["data"]
        
        # Required fields
        assert "flag_id" in flag
        assert flag["tenant_id"] == test_tenant_id
        assert flag["flag_key"] == flag_data["flag_key"]
        assert flag["flag_name"] == flag_data["flag_name"]
        assert flag["description"] == flag_data["description"]
        assert flag["flag_type"] == flag_data["flag_type"]
        assert flag["default_value"] == flag_data["default_value"]
        assert flag["is_enabled"] == flag_data["is_enabled"]
        
        # Conditions should be preserved
        assert flag["conditions"] == flag_data["conditions"]

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_create_string_feature_flag_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test POST /api/v1/admin/feature-flags with string flag."""
        flag_data = {
            "flag_key": "contract_test_string_flag",
            "flag_name": "Contract Test String Feature",
            "description": "String feature flag for contract testing",
            "flag_type": "STRING",
            "default_value": "default_theme",
            "is_enabled": True,
            "conditions": {
                "variants": {
                    "blue_theme": {
                        "rollout_percentage": 30,
                        "user_attributes": {"region": "us-east"}
                    },
                    "green_theme": {
                        "rollout_percentage": 20,
                        "user_attributes": {"region": "us-west"}
                    }
                }
            }
        }
        
        response = await client.post(
            "/api/v1/admin/feature-flags",
            headers=superadmin_headers,
            params={"tenant_id": test_tenant_id},
            json=flag_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        flag = data["data"]
        assert flag["flag_type"] == "STRING"
        assert flag["default_value"] == "default_theme"

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_create_json_feature_flag_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test POST /api/v1/admin/feature-flags with JSON flag."""
        flag_data = {
            "flag_key": "contract_test_json_flag",
            "flag_name": "Contract Test JSON Feature",
            "description": "JSON feature flag for contract testing",
            "flag_type": "JSON",
            "default_value": {
                "theme": "default",
                "max_items": 10,
                "features": ["search", "filter"]
            },
            "is_enabled": True
        }
        
        response = await client.post(
            "/api/v1/admin/feature-flags",
            headers=superadmin_headers,
            params={"tenant_id": test_tenant_id},
            json=flag_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        flag = data["data"]
        assert flag["flag_type"] == "JSON"
        assert flag["default_value"] == flag_data["default_value"]

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_create_feature_flag_validation_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test POST /api/v1/admin/feature-flags validation contract."""
        # Invalid flag_type
        invalid_data = {
            "flag_key": "invalid_flag",
            "flag_name": "Invalid Flag",
            "flag_type": "INVALID_TYPE",  # Invalid
            "default_value": True
        }
        
        response = await client.post(
            "/api/v1/admin/feature-flags",
            headers=superadmin_headers,
            params={"tenant_id": test_tenant_id},
            json=invalid_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_create_feature_flag_duplicate_key_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test POST /api/v1/admin/feature-flags duplicate key validation."""
        flag_data = {
            "flag_key": "duplicate_key_test",
            "flag_name": "Duplicate Key Test",
            "flag_type": "BOOLEAN",
            "default_value": False
        }
        
        # Create first flag
        response1 = await client.post(
            "/api/v1/admin/feature-flags",
            headers=superadmin_headers,
            params={"tenant_id": test_tenant_id},
            json=flag_data
        )
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Try to create duplicate
        response2 = await client.post(
            "/api/v1/admin/feature-flags",
            headers=superadmin_headers,
            params={"tenant_id": test_tenant_id},
            json=flag_data
        )
        
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        data = response2.json()
        assert "error" in data
        assert "duplicate" in data["error"]["message"].lower() or "exists" in data["error"]["message"].lower()

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_get_feature_flag_by_id_contract(self, client: AsyncClient, superadmin_headers, test_feature_flag_id):
        """Test GET /api/v1/admin/feature-flags/{flag_id} contract."""
        response = await client.get(
            f"/api/v1/admin/feature-flags/{test_feature_flag_id}",
            headers=superadmin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "data" in data
        flag = data["data"]
        assert flag["flag_id"] == test_feature_flag_id

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_update_feature_flag_contract(self, client: AsyncClient, superadmin_headers, test_feature_flag_id):
        """Test PUT /api/v1/admin/feature-flags/{flag_id} contract."""
        update_data = {
            "flag_name": "Updated Feature Flag Name",
            "description": "Updated description",
            "is_enabled": False,
            "conditions": {
                "rollout_percentage": 25,
                "user_roles": ["user"]
            }
        }
        
        response = await client.put(
            f"/api/v1/admin/feature-flags/{test_feature_flag_id}",
            headers=superadmin_headers,
            json=update_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        flag = data["data"]
        assert flag["flag_name"] == update_data["flag_name"]
        assert flag["description"] == update_data["description"]
        assert flag["is_enabled"] == update_data["is_enabled"]
        assert flag["conditions"] == update_data["conditions"]

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_delete_feature_flag_contract(self, client: AsyncClient, superadmin_headers, test_feature_flag_id):
        """Test DELETE /api/v1/admin/feature-flags/{flag_id} contract."""
        response = await client.delete(
            f"/api/v1/admin/feature-flags/{test_feature_flag_id}",
            headers=superadmin_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not response.content

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_tenant_admin_list_feature_flags_scoped_contract(self, client: AsyncClient, tenant_admin_headers):
        """Test that tenant_admin can only see feature flags in their tenant."""
        response = await client.get("/api/v1/admin/feature-flags", headers=tenant_admin_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # All flags should belong to the same tenant
        if data["data"]:
            tenant_id = data["data"][0]["tenant_id"]
            for flag in data["data"]:
                assert flag["tenant_id"] == tenant_id

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_tenant_admin_cross_tenant_flag_forbidden_contract(
        self, client: AsyncClient, tenant_admin_headers
    ):
        """Test that tenant_admin cannot create feature flags for other tenants."""
        other_tenant_id = "11111111-1111-1111-1111-111111111111"
        flag_data = {
            "flag_key": "unauthorized_flag",
            "flag_name": "Unauthorized Flag",
            "flag_type": "BOOLEAN",
            "default_value": True
        }
        
        response = await client.post(
            "/api/v1/admin/feature-flags",
            headers=tenant_admin_headers,
            params={"tenant_id": other_tenant_id},
            json=flag_data
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_standard_user_access_forbidden_contract(self, client: AsyncClient, user_headers):
        """Test that standard users cannot access admin feature flag endpoints."""
        response = await client.get("/api/v1/admin/feature-flags", headers=user_headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_unauthenticated_access_contract(self, client: AsyncClient):
        """Test that unauthenticated requests are rejected."""
        response = await client.get("/api/v1/admin/feature-flags")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_global_feature_flag_contract(self, client: AsyncClient, superadmin_headers):
        """Test creating global feature flags (tenant_id = null)."""
        flag_data = {
            "flag_key": "global_maintenance_mode",
            "flag_name": "Global Maintenance Mode",
            "description": "System-wide maintenance mode flag",
            "flag_type": "BOOLEAN",
            "default_value": False,
            "is_enabled": True
        }
        
        # No tenant_id parameter for global flags
        response = await client.post(
            "/api/v1/admin/feature-flags",
            headers=superadmin_headers,
            json=flag_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        flag = data["data"]
        assert flag["tenant_id"] is None  # Global flag
        assert flag["flag_key"] == flag_data["flag_key"]

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_tenant_admin_cannot_create_global_flags_contract(
        self, client: AsyncClient, tenant_admin_headers
    ):
        """Test that tenant_admin cannot create global feature flags."""
        flag_data = {
            "flag_key": "unauthorized_global_flag",
            "flag_name": "Unauthorized Global Flag",
            "flag_type": "BOOLEAN",
            "default_value": True
        }
        
        # No tenant_id parameter attempts to create global flag
        response = await client.post(
            "/api/v1/admin/feature-flags",
            headers=tenant_admin_headers,
            json=flag_data
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN