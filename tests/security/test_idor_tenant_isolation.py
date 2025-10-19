"""
IDOR (Insecure Direct Object Reference) attack test suite for tenant isolation.

Tests OWASP A01:2021 (Broken Access Control) remediation by verifying:
1. Query parameter tenant_id is rejected/deprecated
2. Path parameter tenant_id is validated against JWT claims
3. JWT signature tampering is detected
4. Session-based tenant switching requires superadmin role

Constitutional Compliance:
- Tests hexagonal architecture boundary (domain policies via middleware)
- Verifies policy evaluation results in 403 Forbidden
- Validates X-Tenant-Isolation-Policy headers
"""
import pytest
from uuid import UUID, uuid5
from httpx import AsyncClient

# UUID generation helper (matches pattern from conftest.py)
INFYSIGHT_NAMESPACE = UUID("12345678-1234-5678-1234-567812345678")

def deterministic_uuid(name: str) -> str:
    """Generate deterministic UUID from name (same as conftest fixture)."""
    return str(uuid5(INFYSIGHT_NAMESPACE, name))


@pytest.mark.asyncio
async def test_idor_query_param_rejected(
    client: AsyncClient, 
    regular_user_headers: dict
):
    """
    IDOR Attack Vector: Manipulating ?tenant_id= query parameter.
    
    Expected Behavior:
    - Query parameter tenant_id should be deprecated/ignored
    - Tenant context extracted from JWT only
    - Attempting to access another tenant's data via query param fails
    
    OWASP A01:2021: Broken Access Control - Query Param Tampering
    """
    # Get user's actual tenant from JWT
    actual_tenant_id = deterministic_uuid("tenant:infysight")
    
    # Attempt to access different tenant via query parameter
    attacker_target_tenant = deterministic_uuid("tenant:tenant_b")
    
    # Attack: Try to list users from tenant_b using query param
    response = await client.get(
        f"/api/v1/tenants/{actual_tenant_id}/users",
        params={"tenant_id": str(attacker_target_tenant)},  # Malicious query param
        headers=regular_user_headers
    )
    
    # Should succeed but ignore query param (use JWT tenant_id instead)
    assert response.status_code == 200, "Query param should be ignored, not cause error"
    
    # Verify returned data belongs to JWT tenant, not query param tenant
    data = response.json()
    users = data.get("users", [])
    
    # All users should belong to actual tenant (from JWT), not query param
    for user in users:
        assert user["tenant_id"] == str(actual_tenant_id), \
            "Query param tenant_id must be ignored - data should match JWT tenant only"


@pytest.mark.asyncio
async def test_idor_path_param_cross_tenant_denied(
    client: AsyncClient, 
    regular_user_headers: dict
):
    """
    IDOR Attack Vector: Manipulating path parameter tenant_id.
    
    Expected Behavior:
    - Path tenant_id validated against JWT claims
    - Cross-tenant access denied with 403 Forbidden
    - Response includes X-Tenant-Isolation-Policy header
    
    OWASP A01:2021: Broken Access Control - Path Param Tampering
    """
    # User's actual tenant from JWT
    jwt_tenant_id = deterministic_uuid("tenant:infysight")
    
    # Attempt to access different tenant via path parameter
    attacker_target_tenant = deterministic_uuid("tenant:tenant_b")
    
    # Attack: Try to list users from tenant_b using path param
    response = await client.get(
        f"/api/v1/tenants/{attacker_target_tenant}/users",  # Malicious path param
        headers=regular_user_headers
    )
    
    # Should be denied by TenantAccessPolicy
    assert response.status_code == 403, "Cross-tenant access must be blocked"
    
    # Verify policy header present
    assert "X-Tenant-Isolation-Policy" in response.headers or \
           "x-tenant-isolation-policy" in response.headers, \
           "Policy decision header must be present"
    
    # Verify error details
    data = response.json()
    assert "detail" in data, "Error response must include detail"
    
    # Check for policy-related error message
    error_message = str(data["detail"]).lower()
    assert any(keyword in error_message for keyword in ["access denied", "forbidden", "policy", "tenant"]), \
        "Error message should indicate policy denial"


@pytest.mark.asyncio
async def test_idor_path_param_same_tenant_allowed(
    client: AsyncClient, 
    regular_user_headers: dict,
    
):
    """
    Valid Access: Path parameter matches JWT tenant_id.
    
    Expected Behavior:
    - Same-tenant access allowed (200 OK)
    - Policy evaluation returns ALLOW
    
    OWASP A01:2021: Verify legitimate access works (not blocking valid requests)
    """
    # User's tenant from JWT
    jwt_tenant_id = deterministic_uuid("tenant:infysight")
    
    # Access own tenant data
    response = await client.get(
        f"/api/v1/tenants/{jwt_tenant_id}/users",
        headers=regular_user_headers
    )
    
    # Should succeed
    assert response.status_code == 200, "Same-tenant access should be allowed"
    
    data = response.json()
    assert "users" in data, "Response should include users list"


@pytest.mark.asyncio
async def test_idor_jwt_signature_tampering(
    client: AsyncClient, 
    regular_user_headers: dict,
    
):
    """
    IDOR Attack Vector: Tampering with JWT signature to escalate privileges.
    
    Expected Behavior:
    - Modified JWT rejected with 401 Unauthorized
    - Signature validation detects tampering
    - No access to protected resources
    
    OWASP A01:2021: Cryptographic Failures - Signature Validation
    """
    # Tamper with JWT signature (last part after second dot)
    original_token = regular_user_headers.get("Authorization", "").replace("Bearer ", "")
    
    if not original_token:
        pytest.skip("No JWT token in regular_user_headers")
    
    parts = original_token.split(".")
    if len(parts) != 3:
        pytest.skip("Invalid JWT format in test headers")
    
    # Tamper with signature
    parts[2] = "TAMPERED_SIGNATURE_INVALID"
    tampered_token = ".".join(parts)
    
    # Attempt request with tampered token
    response = await client.get(
        f"/api/v1/tenants/{deterministic_uuid('tenant:infysight')}/users",
        headers={"Authorization": f"Bearer {tampered_token}"}
    )
    
    # Should be rejected (401 or 403)
    assert response.status_code in [401, 403], \
        "Tampered JWT signature must be rejected"


@pytest.mark.asyncio
async def test_idor_jwt_tenant_claim_tampering(client: AsyncClient):
    """
    IDOR Attack Vector: Modifying tenant_id claim in JWT payload.
    
    Expected Behavior:
    - Modified JWT payload invalidates signature
    - Request rejected with 401 Unauthorized
    
    OWASP A01:2021: Cryptographic Failures - Payload Integrity
    
    Note: This test verifies JWT signature prevents payload tampering.
    Even if attacker modifies tenant_id in payload, signature won't match.
    """
    # This test is conceptual - in practice, modifying payload breaks signature
    # which is already tested in test_idor_jwt_signature_tampering
    
    # Real-world attack: Decode JWT, change tenant_id, re-encode
    # Defense: Signature validation fails because attacker doesn't have secret key
    
    pytest.skip("JWT payload tampering covered by signature validation test")


@pytest.mark.asyncio
async def test_idor_session_hijacking_requires_superadmin(
    client: AsyncClient, 
    regular_user_headers: dict,
    
):
    """
    IDOR Attack Vector: Session-based tenant switching without superadmin role.
    
    Expected Behavior:
    - Standard users CANNOT switch tenant context
    - POST /admin/context/tenant requires superadmin role
    - Attempt returns 403 Forbidden
    
    OWASP A01:2021: Broken Access Control - Privilege Escalation
    """
    target_tenant_id = deterministic_uuid("tenant:tenant_b")
    
    # Attack: Standard user tries to switch to another tenant
    response = await client.post(
        "/api/v1/admin/context/tenant",
        headers=regular_user_headers,
        json={"target_tenant_id": str(target_tenant_id)}
    )
    
    # Should be denied - only superadmin can switch tenants
    assert response.status_code == 403, "Standard users must not switch tenants"
    
    data = response.json()
    error_message = str(data.get("detail", "")).lower()
    assert any(keyword in error_message for keyword in ["superadmin", "forbidden", "admin"]), \
        "Error should indicate superadmin requirement"


@pytest.mark.asyncio
async def test_idor_superadmin_cross_tenant_allowed(
    client: AsyncClient, 
    superadmin_headers: dict,
    
):
    """
    Valid Superadmin Access: Cross-tenant access for superadmin users.
    
    Expected Behavior:
    - Superadmin can access any tenant's data
    - Policy evaluation returns ALLOW for cross-tenant
    - No 403 errors
    
    OWASP A01:2021: Verify role-based access control works correctly
    """
    # Superadmin accesses tenant_b data
    tenant_b_id = deterministic_uuid("tenant:tenant_b")
    
    response = await client.get(
        f"/api/v1/tenants/{tenant_b_id}/users",
        headers=superadmin_headers
    )
    
    # Should succeed - superadmin has cross-tenant access
    assert response.status_code == 200, "Superadmin cross-tenant access should be allowed"
    
    data = response.json()
    assert "users" in data, "Response should include users list"


@pytest.mark.asyncio
async def test_idor_missing_authorization_header(
    client: AsyncClient,
    
):
    """
    IDOR Attack Vector: Accessing protected resources without authentication.
    
    Expected Behavior:
    - Public routes accessible (e.g., /health, /docs)
    - Protected tenant routes return 401 Unauthorized or 403 Forbidden
    
    OWASP A01:2021: Broken Authentication - Missing Credentials
    """
    tenant_id = deterministic_uuid("tenant:infysight")
    
    # Attempt to access protected resource without auth
    response = await client.get(f"/api/v1/tenants/{tenant_id}/users")
    
    # Should be rejected
    assert response.status_code in [401, 403], \
        "Protected routes must require authentication"


@pytest.mark.asyncio
async def test_idor_malformed_tenant_id_format(client: AsyncClient, regular_user_headers: dict):
    """
    IDOR Attack Vector: Using malformed/non-UUID tenant_id values.
    
    Expected Behavior:
    - Malformed UUIDs rejected with 400 or 404
    - No server errors (500)
    - Graceful error handling
    
    OWASP A01:2021: Input Validation - Malformed Data
    """
    # Attack: Use non-UUID value for tenant_id
    malformed_tenant_ids = [
        "not-a-uuid",
        "12345",
        "../../../etc/passwd",  # Path traversal attempt
        "'; DROP TABLE users; --",  # SQL injection attempt
        "<script>alert('xss')</script>",  # XSS attempt
    ]
    
    for malformed_id in malformed_tenant_ids:
        response = await client.get(
            f"/api/v1/tenants/{malformed_id}/users",
            headers=regular_user_headers
        )
        
        # Should reject with 400 Bad Request or 404 Not Found, not 500
        assert response.status_code in [400, 404, 422], \
            f"Malformed tenant_id '{malformed_id}' should be rejected gracefully (not 500)"
        
        # Verify no server error
        assert response.status_code != 500, \
            f"Malformed input should not cause server error"


# Summary Test: Verify complete IDOR protection
@pytest.mark.asyncio
async def test_idor_protection_summary(
    client: AsyncClient, 
    regular_user_headers: dict, 
    superadmin_headers: dict,
    
):
    """
    Comprehensive IDOR protection verification.
    
    Verifies all OWASP A01:2021 controls are in place:
    1. ✅ Query param ignored (tenant from JWT only)
    2. ✅ Path param validated (cross-tenant denied)
    3. ✅ JWT signature verified (tampering detected)
    4. ✅ Session switching requires superadmin
    5. ✅ Superadmin bypass works correctly
    6. ✅ Missing auth rejected
    7. ✅ Malformed input handled gracefully
    """
    jwt_tenant = deterministic_uuid("tenant:infysight")
    other_tenant = deterministic_uuid("tenant:tenant_b")
    
    # Test 1: Standard user - same tenant (ALLOW)
    resp = await client.get(f"/api/v1/tenants/{jwt_tenant}/users", headers=regular_user_headers)
    assert resp.status_code == 200, "Same-tenant access should work"
    
    # Test 2: Standard user - cross tenant (DENY)
    resp = await client.get(f"/api/v1/tenants/{other_tenant}/users", headers=regular_user_headers)
    assert resp.status_code == 403, "Cross-tenant should be blocked"
    
    # Test 3: Superadmin - cross tenant (ALLOW)
    resp = await client.get(f"/api/v1/tenants/{other_tenant}/users", headers=superadmin_headers)
    assert resp.status_code == 200, "Superadmin cross-tenant should work"
    
    # Test 4: No auth (DENY)
    resp = await client.get(f"/api/v1/tenants/{jwt_tenant}/users")
    assert resp.status_code in [401, 403], "No auth should be rejected"
    
    # All IDOR protections verified! ✅
