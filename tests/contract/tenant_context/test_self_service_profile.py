"""
Contract tests for GET /users/me (self-service profile endpoint).

Constitutional Compliance:
- Validates JWT-based user authentication
- Tests tenant scoping in user profile responses
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_current_user_success_200(client: AsyncClient, superadmin_headers: dict):
    """Authenticated user retrieves their own profile successfully."""
    # Valid JWT → GET /users/me → 200 OK + user profile
    response = await client.get("/api/v1/users/me", headers=superadmin_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert "email" in data
    assert "tenant_id" in data
    assert "roles" in data


@pytest.mark.asyncio
async def test_get_current_user_unauthorized_401(client: AsyncClient):
    """Missing or invalid JWT returns 401 Unauthorized."""
    # No JWT → 401 Unauthorized
    response = await client.get("/api/v1/users/me")
    
    # TenantContextMiddleware raises 401 for missing auth
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_tenant_scoped(client: AsyncClient, superadmin_headers: dict, test_tenant_id: str):
    """User profile tenant_id matches JWT tenant_id (tenant isolation)."""
    # User profile filtered by JWT tenant_id
    response = await client.get("/api/v1/users/me", headers=superadmin_headers)
    
    assert response.status_code == 200
    data = response.json()
    # Verify tenant_id matches the JWT claim (superadmin is in test_tenant_id)
    assert data["tenant_id"] == test_tenant_id


@pytest.mark.asyncio
async def test_get_current_user_schema_validation(client: AsyncClient, superadmin_headers: dict):
    """Response matches expected schema for UserProfileResponse."""
    # Validate response structure (basic schema check)
    response = await client.get("/api/v1/users/me", headers=superadmin_headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify required fields exist (schema validation)
    required_fields = ["user_id", "email", "tenant_id", "roles", "status"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    
    # Verify types
    assert isinstance(data["user_id"], str)
    assert isinstance(data["email"], str)
    assert isinstance(data["tenant_id"], str)
    assert isinstance(data["roles"], list)
