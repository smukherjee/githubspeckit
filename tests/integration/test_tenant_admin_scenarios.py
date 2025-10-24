"""Integration test: Scenario 2 - Tenant Admin User Management.

Tests tenant admin ability to:
1. List users within their own tenant (auto-scoped)
2. Create new users in own tenant
3. Update user information
4. Verify cross-tenant access is denied

This test validates tenant admin RBAC permissions and tenant isolation.
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
@pytest.mark.integration
async def test_tenant_admin_user_management(
    client: AsyncClient,
    tenant_admin_headers,
    test_tenant_id,
):
    """Tenant admin manages users within their tenant only."""
    
    # 1. List users in own tenant (should auto-scope)
    response = await client.get("/api/v1/users", headers=tenant_admin_headers)
    assert response.status_code == 200, f"Failed to list users: {response.text}"
    
    users_data = response.json()
    initial_user_count = len(users_data["users"])
    
    # All users should belong to the tenant admin's tenant
    for user in users_data["users"]:
        assert user["tenant_id"] == test_tenant_id, "Tenant admin sees cross-tenant users"
    
    # 2. Create new user in own tenant
    new_user_email = f"developer-{uuid4().hex[:8]}@testtenant.com"
    new_user_data = {
        "tenant_id": test_tenant_id,  # Explicitly specify tenant (auto-scoped for tenant_admin)
        "email": new_user_email,
        "password": "SecurePass123!",
        "roles": ["user"]
    }
    
    create_response = await client.post(
        "/api/v1/users",
        headers=tenant_admin_headers,
        json=new_user_data
    )
    assert create_response.status_code == 201, f"Failed to create user: {create_response.text}"
    
    created_user = create_response.json()
    new_user_id = created_user["user_id"]
    assert created_user["email"] == new_user_email
    assert created_user["tenant_id"] == test_tenant_id
    
    # 3. Update user roles (tenant admin can manage roles within their tenant)
    # Note: For now, only system roles are supported. Custom roles require creation first.
    update_data = {
        "roles": ["user", "tenant_admin"]  # Use system roles only
    }
    
    update_response = await client.put(
        f"/api/v1/users/{new_user_id}",
        headers=tenant_admin_headers,
        json=update_data
    )
    assert update_response.status_code == 200, f"Failed to update user: {update_response.text}"
    
    updated_user = update_response.json()
    assert "tenant_admin" in updated_user["roles"], "Updated roles not reflected"
    
    # 4. Try to access different tenant (should fail with 403)
    other_tenant_id = str(uuid4())
    cross_tenant_response = await client.get(
        f"/api/v1/users?tenant_id={other_tenant_id}",
        headers=tenant_admin_headers
    )
    assert cross_tenant_response.status_code == 403, "Tenant admin should not access other tenant data"
    
    # 5. Verify user count increased in own tenant
    final_response = await client.get("/api/v1/users", headers=tenant_admin_headers)
    final_user_count = len(final_response.json()["users"])
    assert final_user_count == initial_user_count + 1, "User count should increase by 1"

