"""
Contract Test: T014 - Email uniqueness enforced per-tenant (same tenant conflict)

Tests that duplicate email addresses within the SAME tenant are rejected:
- POST same email twice to same tenant -> 409 on second attempt

Expected to FAIL until Phase 3.3 implementation (T034-T045)
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
async def test_duplicate_email_same_tenant_rejected(
    test_client: AsyncClient,
    superadmin_token: str
):
    """V1.0 enforces email uniqueness within a tenant"""
    
    tenant_id = str(uuid4())
    test_email = f"duplicate-test-{uuid4()}@example.com"
    
    # Create tenant first (as superadmin)
    tenant_response = await test_client.post(
        "/api/v1/admin/tenants",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"name": f"Test Tenant {tenant_id}"}
    )
    assert tenant_response.status_code == 201, (
        f"Failed to create test tenant: {tenant_response.text}"
    )
    created_tenant_id = tenant_response.json()["tenant_id"]
    
    # First user with email should succeed
    user1_response = await test_client.post(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "email": test_email,
            "password": "SecurePass123!",
            "tenant_id": created_tenant_id
        }
    )
    assert user1_response.status_code == 201, (
        f"First user creation should succeed: {user1_response.text}"
    )
    
    # Second user with SAME email in SAME tenant should fail with 409
    user2_response = await test_client.post(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "email": test_email,
            "password": "DifferentPass456!",
            "tenant_id": created_tenant_id
        }
    )
    assert user2_response.status_code == 409, (
        f"Expected 409 for duplicate email in same tenant, got {user2_response.status_code}: {user2_response.text}"
    )
    
    # Error message should mention email conflict
    error_data = user2_response.json()
    assert "email" in error_data.get("detail", "").lower(), (
        "Error message should mention email conflict"
    )


@pytest.mark.asyncio
async def test_case_insensitive_email_uniqueness_same_tenant(
    test_client: AsyncClient,
    superadmin_token: str
):
    """V1.0 enforces case-insensitive email uniqueness within tenant"""
    
    tenant_id = str(uuid4())
    base_email = f"case-test-{uuid4()}@example.com"
    
    # Create tenant
    tenant_response = await test_client.post(
        "/api/v1/admin/tenants",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"name": f"Case Test Tenant {tenant_id}"}
    )
    assert tenant_response.status_code == 201
    created_tenant_id = tenant_response.json()["tenant_id"]
    
    # Create user with lowercase email
    user1_response = await test_client.post(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "email": base_email.lower(),
            "password": "SecurePass123!",
            "tenant_id": created_tenant_id
        }
    )
    assert user1_response.status_code == 201
    
    # Attempt to create user with UPPERCASE version of same email
    user2_response = await test_client.post(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "email": base_email.upper(),
            "password": "DifferentPass456!",
            "tenant_id": created_tenant_id
        }
    )
    assert user2_response.status_code == 409, (
        f"Expected 409 for case-insensitive email conflict, got {user2_response.status_code}"
    )
