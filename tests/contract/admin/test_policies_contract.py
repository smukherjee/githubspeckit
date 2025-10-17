"""
Contract tests for admin policy endpoints.
Tests API shape, request/response schemas, and status codes.
These tests MUST FAIL until implementation is complete.
"""
import pytest
from httpx import AsyncClient
from fastapi import status


class TestAdminPolicyContracts:
    """Contract tests for /api/v1/admin/policies endpoints."""

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_list_policies_contract(self, client: AsyncClient, superadmin_headers):
        """Test GET /api/v1/admin/policies contract."""
        response = await client.get("/api/v1/admin/policies", headers=superadmin_headers)
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)
        
        # If data exists, validate policy structure
        if data["data"]:
            policy = data["data"][0]
            required_fields = [
                "policy_id", "tenant_id", "name", "resource", "action",
                "effect", "roles", "priority", "is_active",
                "created_at", "updated_at", "created_by", "updated_by"
            ]
            for field in required_fields:
                assert field in policy
            
            # Validate enums and types
            assert policy["effect"] in ["ALLOW", "DENY"]
            assert isinstance(policy["roles"], list)
            assert isinstance(policy["priority"], int)
            assert isinstance(policy["is_active"], bool)

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_list_policies_with_filters_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test GET /api/v1/admin/policies with filters."""
        params = {
            "tenant_id": test_tenant_id,
            "resource": "users",
            "effect": "ALLOW",
            "is_active": True,
            "page": 1,
            "per_page": 10
        }
        
        response = await client.get(
            "/api/v1/admin/policies",
            headers=superadmin_headers,
            params=params
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # All policies should match filters
        for policy in data["data"]:
            assert policy["tenant_id"] == test_tenant_id
            if policy["resource"]:  # May be null/empty
                assert policy["resource"] == "users"
            assert policy["effect"] == "ALLOW"
            assert policy["is_active"] is True

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_create_policy_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test POST /api/v1/admin/policies contract."""
        policy_data = {
            "name": "contract_test_policy",
            "resource": "users",
            "action": "read",
            "effect": "ALLOW",
            "roles": ["tenant_admin", "user"],
            "priority": 100,
            "is_active": True,
            "conditions": {
                "resource_owner": True,
                "same_tenant": True,
                "custom_rules": {
                    "time_of_day": "business_hours"
                }
            }
        }
        
        response = await client.post(
            "/api/v1/admin/policies",
            headers=superadmin_headers,
            params={"tenant_id": test_tenant_id},
            json=policy_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        assert "data" in data
        policy = data["data"]
        
        # Required fields
        assert "policy_id" in policy
        assert policy["tenant_id"] == test_tenant_id
        assert policy["name"] == policy_data["name"]
        assert policy["resource"] == policy_data["resource"]
        assert policy["action"] == policy_data["action"]
        assert policy["effect"] == policy_data["effect"]
        assert policy["roles"] == policy_data["roles"]
        assert policy["priority"] == policy_data["priority"]
        assert policy["is_active"] == policy_data["is_active"]
        
        # Conditions should be preserved
        assert policy["conditions"] == policy_data["conditions"]

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_create_policy_minimal_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test POST /api/v1/admin/policies with minimal required fields."""
        policy_data = {
            "name": "minimal_policy",
            "resource": "audit_events",
            "action": "read",
            "effect": "DENY",
            "roles": ["user"]
        }
        
        response = await client.post(
            "/api/v1/admin/policies",
            headers=superadmin_headers,
            params={"tenant_id": test_tenant_id},
            json=policy_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        policy = data["data"]
        
        # Default values should be applied
        assert policy["priority"] == 100  # Default priority
        assert policy["is_active"] is True  # Default active

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_create_policy_validation_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test POST /api/v1/admin/policies validation contract."""
        # Invalid effect value
        invalid_data = {
            "name": "invalid_policy",
            "resource": "users",
            "action": "read",
            "effect": "MAYBE",  # Invalid
            "roles": ["user"]
        }
        
        response = await client.post(
            "/api/v1/admin/policies",
            headers=superadmin_headers,
            params={"tenant_id": test_tenant_id},
            json=invalid_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_create_policy_duplicate_name_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test POST /api/v1/admin/policies duplicate name validation."""
        policy_data = {
            "name": "duplicate_name_test",
            "resource": "users",
            "action": "read",
            "effect": "ALLOW",
            "roles": ["user"]
        }
        
        # Create first policy
        response1 = await client.post(
            "/api/v1/admin/policies",
            headers=superadmin_headers,
            params={"tenant_id": test_tenant_id},
            json=policy_data
        )
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Try to create duplicate
        response2 = await client.post(
            "/api/v1/admin/policies",
            headers=superadmin_headers,
            params={"tenant_id": test_tenant_id},
            json=policy_data
        )
        
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        data = response2.json()
        assert "error" in data
        assert "duplicate" in data["error"]["message"].lower() or "exists" in data["error"]["message"].lower()

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_get_policy_by_id_contract(self, client: AsyncClient, superadmin_headers, test_policy_id):
        """Test GET /api/v1/admin/policies/{policy_id} contract."""
        response = await client.get(
            f"/api/v1/admin/policies/{test_policy_id}",
            headers=superadmin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "data" in data
        policy = data["data"]
        assert policy["policy_id"] == test_policy_id

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_update_policy_contract(self, client: AsyncClient, superadmin_headers, test_policy_id):
        """Test PUT /api/v1/admin/policies/{policy_id} contract."""
        update_data = {
            "priority": 200,
            "is_active": False,
            "conditions": {
                "resource_owner": False,
                "same_tenant": True
            }
        }
        
        response = await client.put(
            f"/api/v1/admin/policies/{test_policy_id}",
            headers=superadmin_headers,
            json=update_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        policy = data["data"]
        assert policy["priority"] == update_data["priority"]
        assert policy["is_active"] == update_data["is_active"]
        assert policy["conditions"] == update_data["conditions"]

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_delete_policy_contract(self, client: AsyncClient, superadmin_headers, test_policy_id):
        """Test DELETE /api/v1/admin/policies/{policy_id} contract."""
        response = await client.delete(
            f"/api/v1/admin/policies/{test_policy_id}",
            headers=superadmin_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not response.content

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_tenant_admin_list_policies_scoped_contract(self, client: AsyncClient, tenant_admin_headers):
        """Test that tenant_admin can only see policies in their tenant."""
        response = await client.get("/api/v1/admin/policies", headers=tenant_admin_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # All policies should belong to the same tenant
        if data["data"]:
            tenant_id = data["data"][0]["tenant_id"]
            for policy in data["data"]:
                assert policy["tenant_id"] == tenant_id

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_tenant_admin_cross_tenant_policy_forbidden_contract(
        self, client: AsyncClient, tenant_admin_headers
    ):
        """Test that tenant_admin cannot create policies for other tenants."""
        other_tenant_id = "11111111-1111-1111-1111-111111111111"
        policy_data = {
            "name": "unauthorized_policy",
            "resource": "users",
            "action": "read",
            "effect": "ALLOW",
            "roles": ["user"]
        }
        
        response = await client.post(
            "/api/v1/admin/policies",
            headers=tenant_admin_headers,
            params={"tenant_id": other_tenant_id},
            json=policy_data
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_standard_user_access_forbidden_contract(self, client: AsyncClient, user_headers):
        """Test that standard users cannot access admin policy endpoints."""
        response = await client.get("/api/v1/admin/policies", headers=user_headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_unauthenticated_access_contract(self, client: AsyncClient):
        """Test that unauthenticated requests are rejected."""
        response = await client.get("/api/v1/admin/policies")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED