"""
Contract Test: T013 - Admin routes exist and require authentication in V1.0

Tests that admin-prefixed routes exist and return 401/403 (not 404):
- /api/v1/admin/tenants -> 401 (unauthorized)
- /api/v1/admin/users -> 401 (unauthorized)

Expected to FAIL until Phase 3.3 implementation (T037-T041)
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_tenant_routes_exist_require_auth(test_client: AsyncClient):
    """V1.0 admin tenant routes exist and require authentication"""
    
    # GET /api/v1/admin/tenants should require auth (401/403, not 404)
    response = await test_client.get("/api/v1/admin/tenants")
    assert response.status_code in [401, 403], (
        f"Expected 401/403 for unauthenticated /api/v1/admin/tenants, got {response.status_code}. "
        "404 means route does not exist."
    )
    
    # POST /api/v1/admin/tenants should require auth
    response = await test_client.post(
        "/api/v1/admin/tenants",
        json={"name": "Test Tenant"}
    )
    assert response.status_code in [401, 403], (
        f"Expected 401/403 for unauthenticated POST /api/v1/admin/tenants, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_admin_user_routes_exist_require_auth(test_client: AsyncClient):
    """V1.0 admin user routes exist and require authentication"""
    
    # GET /api/v1/admin/users should require auth (401/403, not 404)
    response = await test_client.get("/api/v1/admin/users")
    assert response.status_code in [401, 403], (
        f"Expected 401/403 for unauthenticated /api/v1/admin/users, got {response.status_code}. "
        "404 means route does not exist."
    )
    
    # POST /api/v1/admin/users should require auth
    response = await test_client.post(
        "/api/v1/admin/users",
        json={"email": "test@example.com", "password": "SecurePass123!", "tenant_id": "test-tenant"}
    )
    assert response.status_code in [401, 403], (
        f"Expected 401/403 for unauthenticated POST /api/v1/admin/users, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_admin_user_detail_routes_exist_require_auth(test_client: AsyncClient):
    """V1.0 admin user detail routes exist and require authentication"""
    
    test_uuid = "12345678-1234-5678-1234-567812345678"
    
    # GET /api/v1/admin/users/{id} should require auth
    response = await test_client.get(f"/api/v1/admin/users/{test_uuid}")
    assert response.status_code in [401, 403, 404], (
        f"Expected 401/403/404 for GET /api/v1/admin/users/{{id}}, got {response.status_code}"
    )
    
    # PUT /api/v1/admin/users/{id} should require auth
    response = await test_client.put(
        f"/api/v1/admin/users/{test_uuid}",
        json={"email": "updated@example.com"}
    )
    assert response.status_code in [401, 403, 404], (
        f"Expected 401/403/404 for PUT /api/v1/admin/users/{{id}}, got {response.status_code}"
    )
