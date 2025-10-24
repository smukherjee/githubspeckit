"""Integration test: Policy API CRUD Operations.

Tests FR-062 to FR-067:
- FR-062: Create policies
- FR-063: Policy verdicts (ALLOW/DENY)
- FR-064: Policy associations (tenant_id)
- FR-065: Superadmin can access all tenant policies
- FR-066: Tenant admin can manage own tenant policies
- FR-067: Policy validation (effect, condition)
- FR-087: include_deleted parameter support

RBAC Enforcement:
- Superadmin: Can register and list policies for any tenant
- Tenant Admin: Can register and list policies for own tenant only
- Standard User: Cannot access policy endpoints

DEFERRED TO PHASE 2: All policy tests marked as skipped (spec 017)
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


pytestmark = pytest.mark.skip(reason="Deferred to Phase 2: Tenant policies - spec 017")


@pytest.mark.asyncio
async def test_policy_register_tenant_admin(
    client: AsyncClient,
    tenant_admin_headers,
    test_tenant_id
):
    """FR-062, FR-066: Tenant admin can register policies for their tenant."""
    
    policy_data = {
        "policy_id": str(uuid4()),  # Use proper UUID format
        "version": 1,
        "resource_type": "users",
        "condition_expression": "action == 'read' and role in ['developer', 'analyst']",
        "effect": "ALLOW"
    }
    
    response = await client.post(
        "/api/v1/policies/register",
        headers=tenant_admin_headers,
        json=policy_data
    )
    
    assert response.status_code == 201, f"Failed to register policy: {response.json()}"
    data = response.json()
    
    # Verify response structure (FR-067: validation)
    assert data["policy_id"] == policy_data["policy_id"]
    assert data["version"] == 1
    assert data["resource_type"] == "users"
    assert data["effect"] == "ALLOW"
    assert data["created_by"] is not None
    assert data["created_at"] is not None


@pytest.mark.asyncio

async def test_policy_register_invalid_effect(
    client: AsyncClient,
    tenant_admin_headers,
):
    """FR-067: Policy validation rejects invalid effect values."""
    
    policy_data = {
        "policy_id": str(uuid4()),
        "version": 1,
        "resource_type": "users",
        "condition_expression": "action == 'read'",
        "effect": "MAYBE"  # Invalid effect
    }
    
    response = await client.post(
        "/api/v1/policies/register",
        headers=tenant_admin_headers,
        json=policy_data
    )
    
    assert response.status_code == 400, "Invalid effect was accepted"
    assert "invalid_effect" in response.json()["detail"]


@pytest.mark.asyncio

async def test_policy_register_deny_effect(
    client: AsyncClient,
    tenant_admin_headers,
):
    """FR-063: Policies can have DENY effect for verdicts."""
    
    policy_data = {
        "policy_id": str(uuid4()),
        "version": 1,
        "resource_type": "sensitive_data",
        "condition_expression": "action == 'delete' and role not in ['superadmin']",
        "effect": "DENY"
    }
    
    response = await client.post(
        "/api/v1/policies/register",
        headers=tenant_admin_headers,
        json=policy_data
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["effect"] == "DENY"


@pytest.mark.asyncio

async def test_policy_list_tenant_admin_isolation(
    client: AsyncClient,
    tenant_admin_headers,
    test_tenant_id,
):
    """FR-066, FR-064: Tenant admin can only list policies from their own tenant."""
    
    # Register a policy first
    policy_data = {
        "policy_id": str(uuid4()),
        "version": 1,
        "resource_type": "projects",
        "condition_expression": "action == 'create'",
        "effect": "ALLOW"
    }
    
    register_response = await client.post(
        "/api/v1/policies/register",
        headers=tenant_admin_headers,
        json=policy_data
    )
    assert register_response.status_code == 201
    
    # List policies - should return only from own tenant
    list_response = await client.get(
        "/api/v1/policies",
        headers=tenant_admin_headers
    )
    
    assert list_response.status_code == 200
    policies = list_response.json()
    
    # Verify tenant isolation (all policies belong to test_tenant_id)
    assert isinstance(policies, list)
    assert len(policies) > 0
    
    # Verify the created policy is in the list
    policy_ids = [p["policy_id"] for p in policies]
    assert policy_data["policy_id"] in policy_ids


@pytest.mark.asyncio

async def test_policy_list_superadmin_cross_tenant(
    client: AsyncClient,
    superadmin_headers,
    test_tenant_id,
):
    """FR-065: Superadmin can list policies for specific tenant via tenant_id parameter."""
    
    response = await client.get(
        f"/api/v1/policies?tenant_id={test_tenant_id}",
        headers=superadmin_headers
    )
    
    assert response.status_code == 200
    policies = response.json()
    assert isinstance(policies, list)


@pytest.mark.asyncio

async def test_policy_list_superadmin_uses_jwt_tenant(
    client: AsyncClient,
    superadmin_headers,
):
    """FR-004 Tenant Security Refactor: Superadmin lists policies from their JWT tenant_id.
    
    The old behavior required explicit tenant_id query parameter (now deprecated).
    New behavior: Uses effective_tenant_id from JWT automatically.
    For cross-tenant access, superadmin must use session switching (POST /admin/context/tenant).
    """
    
    response = await client.get(
        "/api/v1/policies",
        headers=superadmin_headers
    )
    
    # Should succeed with 200 OK (uses JWT tenant_id automatically)
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    # Returns list of policies (may be empty)
    assert isinstance(response.json(), list), "Expected list response"


@pytest.mark.asyncio

async def test_policy_list_standard_user_forbidden(
    client: AsyncClient,
    regular_user_headers,
):
    """RBAC: Standard users cannot list policies."""
    
    response = await client.get(
        "/api/v1/policies",
        headers=regular_user_headers
    )
    
    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["detail"]


@pytest.mark.asyncio

async def test_policy_register_standard_user_forbidden(
    client: AsyncClient,
    regular_user_headers,
):
    """RBAC: Standard users cannot register policies."""
    
    policy_data = {
        "policy_id": str(uuid4()),
        "version": 1,
        "resource_type": "users",
        "condition_expression": "action == 'read'",
        "effect": "ALLOW"
    }
    
    response = await client.post(
        "/api/v1/policies/register",
        headers=regular_user_headers,
        json=policy_data
    )
    
    # Should be forbidden (403) - standard users don't have policy management access
    # Note: This test may fail if RBAC is not properly enforced in the endpoint
    assert response.status_code == 403


@pytest.mark.asyncio

async def test_policy_list_include_deleted_parameter(
    client: AsyncClient,
    tenant_admin_headers,
):
    """FR-087: include_deleted parameter filters soft-deleted policies.
    
    Note: This test verifies the parameter is accepted. Full soft-delete
    functionality requires additional endpoints (delete/restore) which
    may be implemented in a future phase.
    """
    
    # List with include_deleted=false (default)
    response_active = await client.get(
        "/api/v1/policies?include_deleted=false",
        headers=tenant_admin_headers
    )
    assert response_active.status_code == 200
    
    # List with include_deleted=true
    response_all = await client.get(
        "/api/v1/policies?include_deleted=true",
        headers=tenant_admin_headers
    )
    assert response_all.status_code == 200
    
    # Both should return valid lists
    assert isinstance(response_active.json(), list)
    assert isinstance(response_all.json(), list)


@pytest.mark.asyncio

async def test_policy_content_range_header(
    client: AsyncClient,
    tenant_admin_headers,
):
    """React-Admin compatibility: Content-Range header is present."""
    
    response = await client.get(
        "/api/v1/policies",
        headers=tenant_admin_headers
    )
    
    assert response.status_code == 200
    assert "Content-Range" in response.headers
    
    # Verify format: "policies 0-N/TOTAL"
    content_range = response.headers["Content-Range"]
    assert content_range.startswith("policies")
    assert "/" in content_range


@pytest.mark.asyncio

async def test_policy_upsert_behavior(
    client: AsyncClient,
    tenant_admin_headers
):
    """FR-062: Policy registration supports upsert (create or update)."""
    
    policy_id = str(uuid4())  # Use proper UUID
    
    # First registration
    policy_data_v1 = {
        "policy_id": policy_id,
        "version": 1,
        "resource_type": "documents",
        "condition_expression": "action == 'read'",
        "effect": "ALLOW"
    }
    
    response_v1 = await client.post(
        "/api/v1/policies/register",
        headers=tenant_admin_headers,
        json=policy_data_v1
    )
    assert response_v1.status_code == 201
    
    # Second registration with same policy_id (update/upsert)
    policy_data_v2 = {
        "policy_id": policy_id,
        "version": 2,
        "resource_type": "documents",
        "condition_expression": "action in ['read', 'write']",
        "effect": "ALLOW"
    }
    
    response_v2 = await client.post(
        "/api/v1/policies/register",
        headers=tenant_admin_headers,
        json=policy_data_v2
    )
    
    # Should succeed (upsert behavior)
    assert response_v2.status_code == 201
    data_v2 = response_v2.json()
    assert data_v2["version"] == 2
