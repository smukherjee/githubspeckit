"""
Integration test: RBAC enforcement for /admin/* routes (Quickstart Scenario 5).

Constitutional Compliance:
- Tests role-based access control integration
- Validates AuthorizationMiddleware wired to admin routes

Expected Result: Validates RBAC enforcement for admin routes.
"""

import pytest
import pytest_asyncio
from uuid import uuid5, UUID
from httpx import AsyncClient

INFYSIGHT_NAMESPACE = UUID("12345678-1234-5678-1234-567812345678")


def deterministic_uuid(name: str) -> str:
    """Generate deterministic UUID for testing."""
    return str(uuid5(INFYSIGHT_NAMESPACE, name))


@pytest.mark.asyncio
async def test_standard_user_admin_route_denied(client, regular_user_headers):
    """Standard user CANNOT access /admin/* routes (403 Forbidden)."""
    # Standard user trying to access admin endpoint - should be denied
    # Using tenant switch endpoint as test case (requires superadmin role)
    
    target_tenant_id = deterministic_uuid("tenant:tenant_b")
    
    response = await client.post(
        "/api/v1/admin/context/tenant",
        headers=regular_user_headers,
        json={"target_tenant_id": target_tenant_id}
    )
    
    # Should be denied - user doesn't have superadmin role
    assert response.status_code == 403
    data = response.json()
    # Response has nested detail->error structure
    assert "detail" in data
    assert "error" in data["detail"]
    assert data["detail"]["error"]["code"] == "FORBIDDEN"
    assert "superadmin" in data["detail"]["error"]["message"].lower()


@pytest.mark.asyncio
async def test_tenant_admin_own_routes(client, tenant_admin_headers, test_tenant_id):
    """Tenant admin can pass middleware for /admin/* routes (endpoint-level checks may still apply)."""
    # Test that tenant_admin role passes the AuthorizationMiddleware for /admin/* routes
    # The middleware evaluates TenantAccessPolicy.evaluate_admin_route_access which allows tenant_admin
    # Note: The /admin/context/tenant endpoint has an additional superadmin-only check inside the endpoint
    
    # Try accessing the tenant switch endpoint - should pass middleware but fail at endpoint level
    response = await client.post(
        "/api/v1/admin/context/tenant",
        headers=tenant_admin_headers,
        json={"target_tenant_id": test_tenant_id}
    )
    
    # Should get 403 from endpoint (not middleware) with specific superadmin requirement message
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data
    assert "error" in data["detail"]
    assert data["detail"]["error"]["code"] == "FORBIDDEN"
    # Verify this is the endpoint-level check (superadmin required), not middleware check (admin_role_required)
    assert "superadmin" in data["detail"]["error"]["message"].lower()


@pytest.mark.asyncio
async def test_tenant_admin_cross_tenant_denied(client, tenant_admin_headers, test_tenant_id):
    """Tenant admin CANNOT access resources from other tenants (403 Forbidden)."""
    # Test that tenant_admin from Tenant A cannot access Tenant B resources
    # This validates cross-tenant isolation even with admin role
    
    # Create a different tenant ID (not the tenant_admin's tenant)
    other_tenant_id = deterministic_uuid("tenant:othertenant")
    
    # Tenant admin should NOT be able to access other tenant's users
    response = await client.get(
        f"/api/v1/tenants/{other_tenant_id}/users",
        headers=tenant_admin_headers
    )
    
    # Should return 403 Forbidden from cross-tenant isolation policy
    assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert "detail" in data, "Response should contain error detail"
    
    # Should have tenant isolation policy header
    assert "X-Tenant-Isolation-Policy" in response.headers or "x-tenant-isolation-policy" in response.headers, \
        "Response should contain X-Tenant-Isolation-Policy header"
    
    # Verify the header indicates cross-tenant isolation rule
    policy_header = response.headers.get("X-Tenant-Isolation-Policy") or response.headers.get("x-tenant-isolation-policy")
    assert policy_header == "cross_tenant_isolation", \
        f"Expected 'cross_tenant_isolation' policy rule, got '{policy_header}'"
