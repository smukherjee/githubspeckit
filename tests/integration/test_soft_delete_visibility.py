"""
Integration tests for soft-delete visibility across all entities.

Tests FR-085, FR-086, FR-087: Soft-delete support for policies, feature flags,
users, and tenants with include_deleted query parameter.

Note: These tests verify that the include_deleted parameter is accepted by the
API endpoints and that it defaults to false (only active records returned).
"""
import pytest
from httpx import AsyncClient


class TestIncludeDeletedParameter:
    """Test that include_deleted parameter exists and is accepted."""
    
    async def test_users_accepts_include_deleted_parameter(
        self,
        client: AsyncClient,
        auth_headers: dict,
        seeded_database: dict
    ):
        """Test that users list endpoint accepts include_deleted parameter (FR-087)."""
        tenant_id = seeded_database["tenant_id"]
        
        # Test without parameter (default)
        response = await client.get(
            f"/api/v1/users?tenant_id={tenant_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        default_users = response.json()["users"]
        
        # Test with include_deleted=false
        response = await client.get(
            f"/api/v1/users?tenant_id={tenant_id}&include_deleted=false",
            headers=auth_headers
        )
        assert response.status_code == 200
        exclude_deleted_users = response.json()["users"]
        assert len(exclude_deleted_users) == len(default_users)
        
        # Test with include_deleted=true
        response = await client.get(
            f"/api/v1/users?tenant_id={tenant_id}&include_deleted=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        # Verify parameter is accepted (might have same or more users)
        all_users = response.json()["users"]
        assert len(all_users) >= len(default_users)
    
    async def test_tenants_accepts_include_deleted_parameter(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test that tenants list endpoint accepts include_deleted parameter (FR-087)."""
        # Test without parameter (default)
        response = await client.get(
            "/api/v1/tenants",
            headers=auth_headers
        )
        assert response.status_code == 200
        default_tenants = response.json()["tenants"]
        
        # Test with include_deleted=false
        response = await client.get(
            "/api/v1/tenants?include_deleted=false",
            headers=auth_headers
        )
        assert response.status_code == 200
        exclude_deleted_tenants = response.json()["tenants"]
        assert len(exclude_deleted_tenants) == len(default_tenants)
        
        # Test with include_deleted=true
        response = await client.get(
            "/api/v1/tenants?include_deleted=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        # Verify parameter is accepted
        all_tenants = response.json()["tenants"]
        assert len(all_tenants) >= len(default_tenants)
    
    @pytest.mark.skip(reason="Deferred to Phase 2: Policy engine - spec 014")
    async def test_policies_accepts_include_deleted_parameter(
        self,
        client: AsyncClient,
        auth_headers: dict,
        seeded_database: dict
    ):
        """Test that policies list endpoint accepts include_deleted parameter (FR-085, FR-087)."""
        tenant_id = seeded_database["tenant_id"]
        
        # Test without parameter (default)
        response = await client.get(
            f"/api/v1/policies?tenant_id={tenant_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        default_policies = response.json()  # policies endpoint returns a list directly
        
        # Test with include_deleted=false
        response = await client.get(
            f"/api/v1/policies?tenant_id={tenant_id}&include_deleted=false",
            headers=auth_headers
        )
        assert response.status_code == 200
        exclude_deleted_policies = response.json()
        assert len(exclude_deleted_policies) == len(default_policies)
        
        # Test with include_deleted=true
        response = await client.get(
            f"/api/v1/policies?tenant_id={tenant_id}&include_deleted=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        # Verify parameter is accepted
        all_policies = response.json()
        assert len(all_policies) >= len(default_policies)
    
    @pytest.mark.skip(reason="Deferred to Phase 2: Feature flags - spec 017")
    async def test_feature_flags_accepts_include_deleted_parameter(
        self,
        client: AsyncClient,
        auth_headers: dict,
        seeded_database: dict
    ):
        """Test that feature_flags list endpoint accepts include_deleted parameter (FR-085, FR-087)."""
        tenant_id = seeded_database["tenant_id"]
        
        # Test without parameter (default)
        response = await client.get(
            f"/api/v1/feature-flags?tenant_id={tenant_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        default_flags = response.json()["flags"]
        
        # Test with include_deleted=false
        response = await client.get(
            f"/api/v1/feature-flags?tenant_id={tenant_id}&include_deleted=false",
            headers=auth_headers
        )
        assert response.status_code == 200
        exclude_deleted_flags = response.json()["flags"]
        assert len(exclude_deleted_flags) == len(default_flags)
        
        # Test with include_deleted=true
        response = await client.get(
            f"/api/v1/feature-flags?tenant_id={tenant_id}&include_deleted=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        # Verify parameter is accepted
        all_flags = response.json()["flags"]
        assert len(all_flags) >= len(default_flags)
