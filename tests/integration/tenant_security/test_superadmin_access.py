"""
Integration test: Superadmin cross-tenant access (Quickstart Scenario 2).

Constitutional Compliance:
- Tests superadmin global access bypass
- Validates audit logging for allowed cross-tenant access

Expected Result: Superadmin can access any tenant's resources (200 OK).
"""

import pytest
import pytest_asyncio
from uuid import uuid5, UUID
from httpx import AsyncClient


# Use same namespace as other tests for deterministic UUIDs
INFYSIGHT_NAMESPACE = UUID("12345678-1234-5678-1234-567812345678")


def deterministic_uuid(name: str) -> str:
    """Generate deterministic UUIDs for test data."""
    return str(uuid5(INFYSIGHT_NAMESPACE, name))


@pytest.mark.asyncio
async def test_superadmin_access_tenant_a(client, superadmin_headers, test_tenant_id):
    """Superadmin successfully accesses Tenant A resources (200 OK)."""
    # Scenario: Superadmin logs in → GET /tenants/{tenant_a_id}/users → 200 OK
    
    # Create a tenant ID different from superadmin's home tenant
    tenant_a_id = deterministic_uuid("tenant:tenant_a")
    
    # Superadmin should be able to access ANY tenant (global access)
    response = await client.get(
        f"/api/v1/tenants/{tenant_a_id}/users",
        headers=superadmin_headers
    )
    
    # Should return 200 OK (superadmin bypasses tenant isolation)
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    data = response.json()
    assert "users" in data
    assert "pagination" in data
    assert isinstance(data["users"], list)


@pytest.mark.asyncio
async def test_superadmin_access_tenant_b(client, superadmin_headers):
    """Superadmin successfully accesses Tenant B resources (200 OK)."""
    # Scenario: Superadmin logs in → GET /tenants/{tenant_b_id}/users → 200 OK
    
    # Create a different tenant ID
    tenant_b_id = deterministic_uuid("tenant:tenant_b")
    
    # Superadmin should be able to access ANY tenant (global access)
    response = await client.get(
        f"/api/v1/tenants/{tenant_b_id}/users",
        headers=superadmin_headers
    )
    
    # Should return 200 OK (superadmin bypasses tenant isolation)
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    data = response.json()
    assert "users" in data
    assert "pagination" in data


@pytest.mark.asyncio
async def test_audit_log_cross_tenant_allowed(client, superadmin_headers):
    """Superadmin cross-tenant access creates audit event with rule 'superadmin_global_access'."""
    # Skip this test - audit integration not yet fully implemented (T055 pending)
    pytest.skip("Audit logging for authorization ALLOW decisions not yet fully implemented - T055 pending")
    
    # FUTURE IMPLEMENTATION (when audit is wired):
    # 1. Superadmin accesses other tenant → 200 OK
    # 2. Query audit_events table → Verify event with rule_applied="superadmin_global_access"
    # 3. Verify decision="ALLOW" in audit metadata
