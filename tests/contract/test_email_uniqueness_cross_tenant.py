"""
Contract Test: T015 - Email uniqueness allows cross-tenant duplicates

Tests that the SAME email address can exist in DIFFERENT tenants:
- POST same email to two different tenants -> 201 for both

Expected to FAIL until Phase 3.3 implementation (T034-T045)
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
async def test_same_email_different_tenants_allowed(
    test_client: AsyncClient,
    superadmin_token: str
):
    """V1.0 allows same email in different tenants (tenant-scoped uniqueness)"""
    
    shared_email = f"shared-{uuid4()}@example.com"
    
    # Create first tenant
    tenant1_response = await test_client.post(
        "/api/v1/admin/tenants",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"name": f"Tenant A {uuid4()}"}
    )
    assert tenant1_response.status_code == 201, (
        f"Failed to create first tenant: {tenant1_response.text}"
    )
    tenant1_id = tenant1_response.json()["tenant_id"]
    
    # Create second tenant
    tenant2_response = await test_client.post(
        "/api/v1/admin/tenants",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"name": f"Tenant B {uuid4()}"}
    )
    assert tenant2_response.status_code == 201, (
        f"Failed to create second tenant: {tenant2_response.text}"
    )
    tenant2_id = tenant2_response.json()["tenant_id"]
    
    # Create user with shared email in FIRST tenant
    user1_response = await test_client.post(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "email": shared_email,
            "password": "SecurePass123!",
            "tenant_id": tenant1_id
        }
    )
    assert user1_response.status_code == 201, (
        f"First user creation should succeed: {user1_response.text}"
    )
    user1_id = user1_response.json()["user_id"]
    
    # Create user with SAME email in SECOND tenant - should SUCCEED
    user2_response = await test_client.post(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "email": shared_email,
            "password": "DifferentPass456!",
            "tenant_id": tenant2_id
        }
    )
    assert user2_response.status_code == 201, (
        f"Expected 201 for same email in different tenant, got {user2_response.status_code}: {user2_response.text}"
    )
    user2_id = user2_response.json()["user_id"]
    
    # Verify both users exist and have different IDs
    assert user1_id != user2_id, "Users should have different IDs"
    
    # Verify both users have the same email but different tenants
    user1_data = user1_response.json()
    user2_data = user2_response.json()
    assert user1_data["email"].lower() == shared_email.lower()
    assert user2_data["email"].lower() == shared_email.lower()
    assert user1_data["tenant_id"] == tenant1_id
    assert user2_data["tenant_id"] == tenant2_id


@pytest.mark.asyncio
async def test_multiple_tenants_share_email_pool(
    test_client: AsyncClient,
    superadmin_token: str
):
    """V1.0 allows email reuse across 3+ tenants"""
    
    shared_email = f"multi-tenant-{uuid4()}@example.com"
    tenant_ids = []
    user_ids = []
    
    # Create 3 tenants and a user with the same email in each
    for i in range(3):
        # Create tenant
        tenant_response = await test_client.post(
            "/api/v1/admin/tenants",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={"name": f"Multi-Tenant Test {i} {uuid4()}"}
        )
        assert tenant_response.status_code == 201
        tenant_id = tenant_response.json()["tenant_id"]
        tenant_ids.append(tenant_id)
        
        # Create user with shared email
        user_response = await test_client.post(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={
                "email": shared_email,
                "password": f"SecurePass{i}23!",
                "tenant_id": tenant_id
            }
        )
        assert user_response.status_code == 201, (
            f"User creation in tenant {i} should succeed: {user_response.text}"
        )
        user_id = user_response.json()["user_id"]
        user_ids.append(user_id)
    
    # Verify all users have unique IDs
    assert len(set(user_ids)) == 3, "All users should have unique IDs"
    
    # Verify all tenants are different
    assert len(set(tenant_ids)) == 3, "All tenants should be unique"
