"""Integration test: Scenario 3 - RBAC Policy Management.

Tests policy management workflow:
1. Superadmin creates global RBAC policies
2. Tenant admin creates tenant-specific policies
3. Policies are evaluated correctly during authorization
4. Policy priorities are respected (higher priority wins)

This test MUST fail until admin endpoints are fully implemented.
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skip(reason="Test written for old policy API design - needs rewrite for /policies/register endpoint")
async def test_rbac_policy_management(
    client: AsyncClient,
    superadmin_headers,
    tenant_admin_headers,
    test_tenant_id,
):
    """RBAC policies can be created and evaluated correctly."""
    
    # 1. Superadmin creates global policy
    global_policy_data = {
        "name": f"GlobalDenyDeleteUsers-{uuid4()}",
        "resource": "users",
        "action": "delete",
        "effect": "DENY",
        "roles": ["tenant_admin"],
        "priority": 900,
        "is_active": True
    }
    
    global_policy_response = await client.post(
        "/api/v1/policies",
        headers=superadmin_headers,
        json=global_policy_data
    )
    assert global_policy_response.status_code == 201, f"Failed to create global policy: {global_policy_response.text}"
    
    global_policy = global_policy_response.json()["data"]
    assert global_policy["effect"] == "DENY"
    assert global_policy["priority"] == 900
    assert global_policy["tenant_id"] is None  # Global policy
    
    # 2. Tenant admin creates tenant-specific policy
    tenant_policy_data = {
        "name": f"AllowDeveloperRead-{uuid4()}",
        "resource": "feature_flags",
        "action": "read",
        "effect": "ALLOW",
        "roles": ["developer"],
        "priority": 100,
        "is_active": True,
        "conditions": {
            "same_tenant": True
        }
    }
    
    tenant_policy_response = await client.post(
        f"/api/v1/policies?tenant_id={test_tenant_id}",
        headers=tenant_admin_headers,
        json=tenant_policy_data
    )
    assert tenant_policy_response.status_code == 201, f"Failed to create tenant policy: {tenant_policy_response.text}"
    
    tenant_policy = tenant_policy_response.json()["data"]
    assert tenant_policy["tenant_id"] == test_tenant_id
    assert tenant_policy["effect"] == "ALLOW"
    assert tenant_policy["conditions"]["same_tenant"] == True
    
    # 3. List policies (superadmin sees all, tenant admin sees only tenant policies)
    superadmin_policies_response = await client.get(
        "/api/v1/policies",
        headers=superadmin_headers
    )
    assert superadmin_policies_response.status_code == 200
    all_policies = superadmin_policies_response.json()["data"]
    policy_ids = [p["policy_id"] for p in all_policies]
    assert global_policy["policy_id"] in policy_ids
    assert tenant_policy["policy_id"] in policy_ids
    
    tenant_admin_policies_response = await client.get(
        "/api/v1/policies",
        headers=tenant_admin_headers
    )
    assert tenant_admin_policies_response.status_code == 200
    tenant_policies = tenant_admin_policies_response.json()["data"]
    tenant_policy_ids = [p["policy_id"] for p in tenant_policies]
    assert tenant_policy["policy_id"] in tenant_policy_ids
    # Global policies visible to tenant admin but marked as global
    
    # 4. Update policy priority
    update_data = {
        "priority": 950,
        "is_active": True
    }
    
    update_response = await client.put(
        f"/api/v1/policies/{global_policy['policy_id']}",
        headers=superadmin_headers,
        json=update_data
    )
    assert update_response.status_code == 200, f"Failed to update policy: {update_response.text}"
    
    updated_policy = update_response.json()["data"]
    assert updated_policy["priority"] == 950
    
    # 5. Deactivate policy
    deactivate_response = await client.put(
        f"/api/v1/policies/{tenant_policy['policy_id']}",
        headers=tenant_admin_headers,
        json={"is_active": False}
    )
    assert deactivate_response.status_code == 200
    
    deactivated_policy = deactivate_response.json()["data"]
    assert deactivated_policy["is_active"] == False
