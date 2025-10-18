"""Integration test: Scenario 1 - Superadmin Cross-Tenant Management.

Tests superadmin ability to:
1. List all tenants across tenant boundaries
2. Create new tenants
3. Create users in any tenant (cross-tenant operations)
4. List users across all tenants

This test validates superadmin RBAC permissions and cross-tenant operations.
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
@pytest.mark.integration
async def test_superadmin_cross_tenant_management(
    client: AsyncClient,
    superadmin_headers,
    test_tenant_id,
):
    """Superadmin can manage resources across all tenants."""
    
    # 1. List all tenants (superadmin sees all)
    response = await client.get("/api/v1/tenants", headers=superadmin_headers)
    assert response.status_code == 200, f"Failed to list tenants: {response.text}"
    
    tenants_data = response.json()
    initial_tenant_count = len(tenants_data["tenants"])
    assert initial_tenant_count >= 1, "Should have at least the test tenant"
    
    # 2. Create a new tenant
    new_tenant_slug = f"new-test-tenant-{uuid4().hex[:8]}"
    new_tenant_data = {
        "name": f"NewTestTenant-{uuid4().hex[:8]}",
        "slug": new_tenant_slug
    }
    
    create_response = await client.post(
        "/api/v1/tenants",
        headers=superadmin_headers,
        json=new_tenant_data
    )
    assert create_response.status_code == 201, f"Failed to create tenant: {create_response.text}"
    
    created_tenant = create_response.json()
    new_tenant_id = created_tenant["tenant_id"]
    assert created_tenant["name"] == new_tenant_data["name"]
    assert created_tenant["status"] in ["active", "disabled"]
    
    # 3. Create user in the new tenant (cross-tenant operation)
    new_user_email = f"admin-{uuid4().hex[:8]}@newtesttenant.com"
    new_user_data = {
        "tenant_id": new_tenant_id,  # Specify target tenant
        "email": new_user_email,
        "password": "SecurePass123!",
        "roles": ["tenant_admin"]
    }
    
    create_user_response = await client.post(
        "/api/v1/users",
        headers=superadmin_headers,
        json=new_user_data
    )
    assert create_user_response.status_code == 201, f"Failed to create user: {create_user_response.text}"
    
    created_user = create_user_response.json()
    assert created_user["tenant_id"] == new_tenant_id
    assert created_user["email"] == new_user_email
    assert "tenant_admin" in created_user["roles"]
    
    # 4. List users in the new tenant (cross-tenant query)
    users_response = await client.get(
        f"/api/v1/users?tenant_id={new_tenant_id}",
        headers=superadmin_headers
    )
    assert users_response.status_code == 200, f"Failed to list users: {users_response.text}"
    
    users_data = users_response.json()
    user_emails = [u["email"] for u in users_data["users"]]
    assert new_user_email in user_emails, "Newly created user should appear in tenant user list"
    
    # 5. Verify tenant count increased
    final_tenants_response = await client.get("/api/v1/tenants", headers=superadmin_headers)
    final_tenant_count = len(final_tenants_response.json()["tenants"])
    assert final_tenant_count == initial_tenant_count + 1, "Tenant count should increase by 1"

