"""Integration test: RBAC Boundary - Cross-Tenant Access Prevention.

Tests tenant isolation enforcement:
1. Tenant admin cannot access other tenant's users
2. Tenant admin cannot create resources in other tenants
3. Standard user has limited access
4. Proper 403 Forbidden responses for unauthorized access

This test validates critical RBAC boundaries per Constitution §III.
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
@pytest.mark.integration
async def test_tenant_isolation(
    client: AsyncClient,
    superadmin_headers,
    tenant_admin_headers,
    regular_user_headers,
    test_tenant_id,
):
    """Tenant isolation is enforced across all admin endpoints."""
    
    # Setup: Create a second tenant (as superadmin)
    other_tenant_slug = f"other-tenant-{uuid4().hex[:8]}"
    other_tenant_data = {
        "name": f"OtherTenant-{uuid4().hex[:8]}",
        "slug": other_tenant_slug
    }
    
    other_tenant_response = await client.post(
        "/api/v1/tenants",
        headers=superadmin_headers,
        json=other_tenant_data
    )
    assert other_tenant_response.status_code == 201, f"Setup failed: {other_tenant_response.text}"
    other_tenant_id = other_tenant_response.json()["tenant_id"]
    
    # Create a user in the other tenant
    other_user_email = f"user-{uuid4().hex[:8]}@othertenant.com"
    other_user_data = {
        "tenant_id": other_tenant_id,  # Cross-tenant creation by superadmin
        "email": other_user_email,
        "password": "SecurePass123!",
        "roles": ["user"]
    }
    
    other_user_response = await client.post(
        "/api/v1/users",
        headers=superadmin_headers,
        json=other_user_data
    )
    assert other_user_response.status_code == 201, f"Setup failed: {other_user_response.text}"
    other_user_id = other_user_response.json()["user_id"]
    
    # Test 1: Tenant admin cannot list users from other tenant
    cross_tenant_list_response = await client.get(
        f"/api/v1/users?tenant_id={other_tenant_id}",
        headers=tenant_admin_headers
    )
    assert cross_tenant_list_response.status_code == 403, "Tenant admin should not access other tenant's users"
    
    # Test 2: Tenant admin cannot get specific user from other tenant
    cross_tenant_get_response = await client.get(
        f"/api/v1/users/{other_user_id}",
        headers=tenant_admin_headers
    )
    assert cross_tenant_get_response.status_code in [403, 404], "Tenant admin should not access other tenant's user"
    
    # Test 3: Tenant admin cannot create user in other tenant
    cross_tenant_create_data = {
        "tenant_id": other_tenant_id,  # Try to create in other tenant
        "email": f"hacker-{uuid4().hex[:8]}@othertenant.com",
        "password": "HackPass123!",
        "roles": ["user"]
    }
    
    cross_tenant_create_response = await client.post(
        "/api/v1/users",
        headers=tenant_admin_headers,
        json=cross_tenant_create_data
    )
    assert cross_tenant_create_response.status_code == 403, "Tenant admin should not create user in other tenant"
    
    # Test 4: Tenant admin cannot update user in other tenant
    cross_tenant_update_response = await client.put(
        f"/api/v1/users/{other_user_id}",
        headers=tenant_admin_headers,
        json={"roles": ["admin"]}
    )
    assert cross_tenant_update_response.status_code in [403, 404], "Tenant admin should not update user in other tenant"
    
    # Test 5: Tenant admin cannot delete user in other tenant
    cross_tenant_delete_response = await client.delete(
        f"/api/v1/users/{other_user_id}",
        headers=tenant_admin_headers
    )
    assert cross_tenant_delete_response.status_code in [403, 404], "Tenant admin should not delete user in other tenant"
    
    # Test 6: Tenant admin cannot access other tenant's policies
    # First create a policy in the other tenant
    policy_data = {
        "policy_id": f"test-policy-{uuid4().hex[:8]}",
        "version": 1,
        "resource_type": "test_resource",
        "condition_expression": "true",
        "effect": "ALLOW"
    }
    
    await client.post(
        "/api/v1/policies/register",
        headers=superadmin_headers,
        json=policy_data
    )
    
    # Now try to list policies for other tenant as tenant_admin
    cross_tenant_policies_response = await client.get(
        f"/api/v1/policies?tenant_id={other_tenant_id}",
        headers=tenant_admin_headers
    )
    assert cross_tenant_policies_response.status_code in [400, 403], "Tenant admin should not access other tenant's policies"
    
    # Test 7: Verify tenant admin CAN access their own tenant resources
    own_users_response = await client.get(
        "/api/v1/users",
        headers=tenant_admin_headers
    )
    assert own_users_response.status_code == 200, "Tenant admin should access own tenant"
    
    own_users = own_users_response.json()["users"]
    for user in own_users:
        assert user["tenant_id"] == test_tenant_id, "Tenant admin received cross-tenant data"
    
    # Test 8: Regular user can only access their own profile
    me_response = await client.get(
        "/api/v1/users/me",
        headers=regular_user_headers
    )
    assert me_response.status_code == 200, "Regular user should access own profile"
    
    # Regular user cannot list all users
    list_response = await client.get(
        "/api/v1/users",
        headers=regular_user_headers
    )
    # Regular users may not have access or only see themselves
    assert list_response.status_code in [200, 403], "Unexpected response for regular user list"

