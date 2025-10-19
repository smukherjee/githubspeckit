"""
Contract tests for GET /tenants/{tenant_id}/users (tenant-scoped user listing).

Constitutional Compliance:
- Validates tenant isolation enforcement
- Tests X-Tenant-Isolation-Policy header on 403 responses

Expected Result: Validates OpenAPI contract compliance for tenant-scoped endpoints.
"""

import pytest
import pytest_asyncio
from uuid import uuid5, UUID
from httpx import AsyncClient

INFYSIGHT_NAMESPACE = UUID("12345678-1234-5678-1234-567812345678")


def deterministic_uuid(name: str) -> str:
    """Generate deterministic UUID for testing."""
    return str(uuid5(INFYSIGHT_NAMESPACE, name))


@pytest.mark.asyncio
async def test_list_tenant_users_success_200(client, regular_user_headers, test_tenant_id):
    """User can list users in their own tenant (returns paginated user list)."""
    # User accessing their own tenant (infysight tenant from seeded_database)
    
    response = await client.get(
        f"/api/v1/tenants/{test_tenant_id}/users",
        headers=regular_user_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "pagination" in data
    # Verify structure matches API response (not strict OpenAPI validation)
    assert isinstance(data["users"], list)


@pytest.mark.asyncio
async def test_list_tenant_users_forbidden_403(client, regular_user_headers):
    """Standard user CANNOT list users in other tenants (403 Forbidden with policy header)."""
    # User accessing different tenant - should be denied
    other_tenant_id = deterministic_uuid("tenant:tenant_b")
    
    response = await client.get(
        f"/api/v1/tenants/{other_tenant_id}/users",
        headers=regular_user_headers
    )
    
    assert response.status_code == 403
    # Verify policy header is present (middleware adds this)
    assert "X-Tenant-Isolation-Policy" in response.headers


@pytest.mark.asyncio
async def test_list_tenant_users_superadmin_200(client, superadmin_headers):
    """Superadmin can list users in ANY tenant (global access)."""
    # Superadmin accessing any tenant - should succeed
    any_tenant_id = deterministic_uuid("tenant:tenant_b")
    
    response = await client.get(
        f"/api/v1/tenants/{any_tenant_id}/users",
        headers=superadmin_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "users" in data


@pytest.mark.asyncio
async def test_list_tenant_users_schema_validation(client, regular_user_headers, test_tenant_id):
    """Response schema matches OpenAPI specification using schemathesis validation."""
    import jsonschema
    import yaml
    from pathlib import Path
    
    # Load OpenAPI schema
    schema_path = Path(__file__).parent.parent.parent.parent / "specs" / "004-tenant-security-refactor" / "contracts" / "openapi-tenant-context.yaml"
    with open(schema_path) as f:
        openapi_spec = yaml.safe_load(f)
    
    # User listing their own tenant users - should match OpenAPI schema
    response = await client.get(
        f"/api/v1/tenants/{test_tenant_id}/users",
        headers=regular_user_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Extract the schema for the 200 response from OpenAPI spec
    response_schema = openapi_spec["paths"]["/tenants/{tenant_id}/users"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    
    # Validate response against schema
    try:
        jsonschema.validate(instance=data, schema=response_schema)
    except jsonschema.exceptions.ValidationError as e:
        pytest.fail(f"Response does not match OpenAPI schema: {e.message}")
    
    # Additional explicit checks for clarity
    assert "users" in data, "Response must contain 'users' field"
    assert "pagination" in data, "Response must contain 'pagination' field"
    assert isinstance(data["users"], list), "'users' must be an array"
    assert isinstance(data["pagination"], dict), "'pagination' must be an object"
    
    # Validate each user object structure
    # Note: API returns user_id, not id (matches actual implementation)
    for user in data["users"]:
        assert "user_id" in user, "User must have 'user_id' field"
        assert "tenant_id" in user, "User must have 'tenant_id' field"
        assert "email" in user, "User must have 'email' field"
        assert "roles" in user, "User must have 'roles' field"
        assert isinstance(user["roles"], list), "User 'roles' must be an array"
    
    # Validate pagination object structure
    assert "page" in data["pagination"], "Pagination must have 'page' field"
    assert "per_page" in data["pagination"], "Pagination must have 'per_page' field"
    assert "total" in data["pagination"], "Pagination must have 'total' field"
    assert isinstance(data["pagination"]["page"], int), "Pagination 'page' must be integer"
    assert isinstance(data["pagination"]["per_page"], int), "Pagination 'per_page' must be integer"
    assert isinstance(data["pagination"]["total"], int), "Pagination 'total' must be integer"


@pytest.mark.asyncio
async def test_tenant_isolation_policy_header(client, regular_user_headers):
    """403 responses include X-Tenant-Isolation-Policy header with rule applied."""
    # User accessing different tenant - should return 403 with policy header
    other_tenant_id = deterministic_uuid("tenant:tenant_b")
    
    response = await client.get(
        f"/api/v1/tenants/{other_tenant_id}/users",
        headers=regular_user_headers
    )
    
    assert response.status_code == 403
    assert "X-Tenant-Isolation-Policy" in response.headers
    # Verify header contains policy rule identifier
    policy_header = response.headers["X-Tenant-Isolation-Policy"]
    assert len(policy_header) > 0
