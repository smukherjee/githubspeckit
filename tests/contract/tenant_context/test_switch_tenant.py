"""
Contract tests for POST /admin/context/tenant (tenant switching endpoint).

Constitutional Compliance:
- Validates OpenAPI schema compliance
- Tests superadmin-only tenant switching feature
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime


@pytest.mark.asyncio
async def test_switch_tenant_success_200(
    client: AsyncClient,
    db_session,
    superadmin_headers: dict
):
    """Superadmin successfully switches active tenant, returns TenantSwitchResponse."""
    # Create a second tenant to switch to
    from adapters.persistence.models import TenantModel, TenantStatusEnum
    target_tenant = TenantModel(
        tenant_id=uuid4(),
        name=f"Target Tenant {datetime.utcnow().timestamp()}",
        status=TenantStatusEnum.active
    )
    db_session.add(target_tenant)
    await db_session.commit()
    
    # Perform tenant switch
    response = await client.post(
        "/api/v1/admin/context/tenant",
        json={"target_tenant_id": str(target_tenant.tenant_id)},
        headers=superadmin_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    # Match actual response schema from endpoint
    assert "active_tenant_id" in data
    assert data["active_tenant_id"] == str(target_tenant.tenant_id)
    assert "switched_at" in data
    assert "tenant_name" in data


@pytest.mark.asyncio
async def test_switch_tenant_forbidden_403(
    client: AsyncClient,
    regular_user_headers: dict
):
    """Standard user CANNOT switch tenants (403 Forbidden)."""
    target_tenant_id = uuid4()
    
    response = await client.post(
        "/api/v1/admin/context/tenant",
        json={"target_tenant_id": str(target_tenant_id)},
        headers=regular_user_headers
    )
    
    assert response.status_code == 403
    # Verify error response
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_switch_tenant_not_found_404(
    client: AsyncClient,
    superadmin_headers: dict
):
    """Switching to nonexistent tenant returns 404 Not Found."""
    nonexistent_tenant_id = uuid4()
    
    response = await client.post(
        "/api/v1/admin/context/tenant",
        json={"target_tenant_id": str(nonexistent_tenant_id)},
        headers=superadmin_headers
    )
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    # Handle detail as either string or dict with 'message' field
    detail_msg = data["detail"] if isinstance(data["detail"], str) else str(data["detail"])
    assert "not found" in detail_msg.lower() or "does not exist" in detail_msg.lower()


@pytest.mark.asyncio
async def test_switch_tenant_schema_validation(
    client: AsyncClient,
    db_session,
    superadmin_headers: dict
):
    """Request and response match expected schema."""
    # Create target tenant
    from adapters.persistence.models import TenantModel, TenantStatusEnum
    target_tenant = TenantModel(
        tenant_id=uuid4(),
        name=f"Schema Validation Target {datetime.utcnow().timestamp()}",
        status=TenantStatusEnum.active
    )
    db_session.add(target_tenant)
    await db_session.commit()
    
    # Test with valid request schema
    response = await client.post(
        "/api/v1/admin/context/tenant",
        json={"target_tenant_id": str(target_tenant.tenant_id)},
        headers=superadmin_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Validate response schema fields (match actual response)
    required_fields = ["active_tenant_id", "tenant_name", "switched_at"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    
    # Validate field types
    assert isinstance(data["active_tenant_id"], str)
    assert isinstance(data["tenant_name"], str)
    assert isinstance(data["switched_at"], str)  # ISO datetime string
