"""
Contract Test: T016 - No deprecation headers in V1.0 responses

Tests that deprecation-related headers are NO LONGER present in V1.0:
- X-API-Deprecation
- Sunset
- X-Deprecation-Notice
- Deprecation

Expected to FAIL until Phase 3.3 implementation (T026-T033)
"""
import pytest
from httpx import AsyncClient


DEPRECATION_HEADERS = [
    "x-api-deprecation",
    "sunset",
    "x-deprecation-notice",
    "deprecation",
]


@pytest.mark.asyncio
async def test_health_endpoint_no_deprecation_headers(test_client: AsyncClient):
    """V1.0 health endpoint should not include deprecation headers"""
    
    # V1.0: Only /health endpoint exists (not /api/v1/health)
    response = await test_client.get("/health")
    
    # Check response is successful
    assert response.status_code == 200
    
    # Verify NO deprecation headers present
    response_headers_lower = {k.lower(): v for k, v in response.headers.items()}
    
    for header in DEPRECATION_HEADERS:
        assert header not in response_headers_lower, (
            f"V1.0 should not include '{header}' header. Found: {response_headers_lower.get(header)}"
        )


@pytest.mark.asyncio
async def test_admin_routes_no_deprecation_headers(
    test_client: AsyncClient,
    superadmin_token: str
):
    """V1.0 admin routes should not include deprecation headers"""
    
    # Test admin tenants list
    response = await test_client.get(
        "/api/v1/admin/tenants",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    
    response_headers_lower = {k.lower(): v for k, v in response.headers.items()}
    
    for header in DEPRECATION_HEADERS:
        assert header not in response_headers_lower, (
            f"Admin routes should not include '{header}' header. Found: {response_headers_lower.get(header)}"
        )


@pytest.mark.asyncio
async def test_auth_endpoints_no_deprecation_headers(test_client: AsyncClient):
    """V1.0 auth endpoints should not include deprecation headers"""
    
    # Test login endpoint
    response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "invalidpassword"
        }
    )
    
    response_headers_lower = {k.lower(): v for k, v in response.headers.items()}
    
    for header in DEPRECATION_HEADERS:
        assert header not in response_headers_lower, (
            f"Auth endpoints should not include '{header}' header. Found: {response_headers_lower.get(header)}"
        )


@pytest.mark.asyncio
async def test_openapi_spec_no_deprecation_headers(test_client: AsyncClient):
    """V1.0 OpenAPI spec endpoint should not include deprecation headers"""
    
    response = await test_client.get("/openapi.json")
    
    assert response.status_code == 200
    
    response_headers_lower = {k.lower(): v for k, v in response.headers.items()}
    
    for header in DEPRECATION_HEADERS:
        assert header not in response_headers_lower, (
            f"OpenAPI endpoint should not include '{header}' header. Found: {response_headers_lower.get(header)}"
        )


@pytest.mark.asyncio
async def test_404_responses_no_deprecation_headers(test_client: AsyncClient):
    """V1.0 even 404 responses should not include deprecation headers"""
    
    response = await test_client.get("/api/v1/nonexistent-endpoint")
    
    # May return 401 (auth required) or 404 (not found) depending on middleware order
    assert response.status_code in [401, 404], (
        f"Expected 401 or 404, got {response.status_code}"
    )
    
    response_headers_lower = {k.lower(): v for k, v in response.headers.items()}
    
    for header in DEPRECATION_HEADERS:
        assert header not in response_headers_lower, (
            f"Even error responses should not include '{header}' header. Found: {response_headers_lower.get(header)}"
        )
