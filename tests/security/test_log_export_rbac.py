"""Security tests for log export RBAC enforcement (C1).

Tests verify:
- Authentication required for log export
- Tenant admin can only see logs from their own tenant
- Superadmin can see logs from all tenants
- Regular users are denied access
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_log_export_requires_authentication(client: AsyncClient):
    """GET /api/v1/logs/export requires authentication (no public access)."""
    response = await client.get("/api/v1/logs/export")
    assert response.status_code == 401, "Log export must require authentication"
    # V1.0: Error message changed to "Missing or invalid Authorization header"
    assert "Authorization" in response.json()["detail"]


@pytest.mark.asyncio
async def test_regular_user_denied_log_export_access(client: AsyncClient, regular_user_headers):
    """Regular users cannot access log export (requires admin role)."""
    response = await client.get(
        "/api/v1/logs/export",
        headers=regular_user_headers
    )
    assert response.status_code == 403, "Regular users should be denied log export access"
    assert "superadmin or tenant_admin" in response.json()["detail"]


@pytest.mark.asyncio
async def test_tenant_admin_sees_own_tenant_logs_only(client: AsyncClient, tenant_admin_headers):
    """Tenant admin can export logs from their own tenant only."""
    # Request without tenant_id → should automatically filter to admin's tenant
    response = await client.get(
        "/api/v1/logs/export?limit=10",
        headers=tenant_admin_headers
    )
    assert response.status_code == 200, "Tenant admin should access log export"
    data = response.json()
    
    # Verify response structure
    assert "records" in data
    assert "truncated" in data
    assert "total_available" in data
    
    # All records should belong to tenant admin's tenant (if any logs exist)
    if data["records"]:
        for record in data["records"]:
            # Logs may not have tenant_id if they're global system logs
            # but tenant-specific logs MUST match admin's tenant
            if "tenant_id" in record:
                # Extract tenant_id from JWT in headers
                from jose import jwt
                token = tenant_admin_headers["Authorization"].split(" ")[1]
                # Decode without verification for testing purposes
                decoded = jwt.get_unverified_claims(token)
                admin_tenant_id = decoded.get("tenant_id")
                
                assert record["tenant_id"] == admin_tenant_id, \
                    f"Tenant admin should only see logs from their tenant ({admin_tenant_id})"


@pytest.mark.asyncio
async def test_tenant_admin_cannot_see_other_tenant_logs(client: AsyncClient, tenant_admin_headers):
    """Tenant admin cannot export logs from other tenants."""
    # Try to request logs from a different tenant
    other_tenant_id = "00000000-0000-0000-0000-000000000999"  # Non-existent tenant
    
    response = await client.get(
        f"/api/v1/logs/export?tenant_id={other_tenant_id}",
        headers=tenant_admin_headers
    )
    
    assert response.status_code == 403, "Tenant admin should not access other tenant's logs"
    # V1.0: Error message changed to "Access denied by tenant isolation policy"
    assert "tenant isolation" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_superadmin_can_see_all_tenant_logs(client: AsyncClient, superadmin_headers):
    """Superadmin can export logs from any tenant or all tenants."""
    # Test 1: Request all logs (no tenant_id filter)
    response_all = await client.get(
        "/api/v1/logs/export?limit=10",
        headers=superadmin_headers
    )
    assert response_all.status_code == 200, "Superadmin should access all logs"
    data_all = response_all.json()
    assert "records" in data_all
    
    # Test 2: Request logs from specific tenant (should work for superadmin)
    specific_tenant_id = "00000000-0000-0000-0000-000000000001"
    response_specific = await client.get(
        f"/api/v1/logs/export?tenant_id={specific_tenant_id}&limit=10",
        headers=superadmin_headers
    )
    assert response_specific.status_code == 200, "Superadmin should access specific tenant logs"
    data_specific = response_specific.json()
    assert "records" in data_specific
    
    # All records in filtered response should match requested tenant (if any logs exist)
    if data_specific["records"]:
        for record in data_specific["records"]:
            if "tenant_id" in record:
                assert record["tenant_id"] == specific_tenant_id, \
                    f"Filtered logs should only contain records from tenant {specific_tenant_id}"


@pytest.mark.asyncio
async def test_log_export_filters_work_with_rbac(client: AsyncClient, superadmin_headers):
    """Log export filtering (category, since, until) works with RBAC."""
    from datetime import datetime, timedelta, timezone
    
    # Test category filter
    response_category = await client.get(
        "/api/v1/logs/export?category=info&limit=5",
        headers=superadmin_headers
    )
    assert response_category.status_code == 200
    
    # Test time window filter
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=1)).isoformat()
    until = now.isoformat()
    
    response_time = await client.get(
        f"/api/v1/logs/export?since={since}&until={until}&limit=5",
        headers=superadmin_headers
    )
    assert response_time.status_code == 200
    
    # Test correlation_id filter
    response_corr = await client.get(
        "/api/v1/logs/export?correlation_id=test-correlation-123&limit=5",
        headers=superadmin_headers
    )
    assert response_corr.status_code == 200


@pytest.mark.asyncio
async def test_log_export_respects_time_window_limit(client: AsyncClient, superadmin_headers):
    """Log export enforces 24-hour time window limit (FR-072)."""
    from datetime import datetime, timedelta, timezone
    
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=25)).isoformat()  # >24 hours ago
    until = now.isoformat()
    
    response = await client.get(
        f"/api/v1/logs/export?since={since}&until={until}",
        headers=superadmin_headers
    )
    
    assert response.status_code == 400, "Should reject time windows >24 hours"
    assert "24 hour limit" in response.json()["detail"]
