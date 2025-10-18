"""Security tests for HTTP cache headers (OWASP A01:2021 compliance).

Tests verify that sensitive API endpoints have proper Cache-Control headers
to prevent browser/proxy caching of authentication tokens, user data, and
authorization policies.

Addresses: CWE-525 (Use of Web Browser Cache Containing Sensitive Information)
OWASP: A01:2021 – Broken Access Control
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.security
async def test_auth_login_endpoint_prevents_caching(
    client: AsyncClient,
) -> None:
    """Auth login endpoint MUST have no-store cache headers.
    
    Risk: Access tokens cached in browser expose credentials to:
    - Shared computer users
    - Browser forensics tools
    - Local file system attackers
    """
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@example.com",
            "password": "admin123",
        },
    )
    
    # Verify response succeeded (or 401 if credentials wrong)
    assert response.status_code in [200, 401]
    
    # CRITICAL: Must prevent all caching
    assert "Cache-Control" in response.headers, "Missing Cache-Control header"
    cache_control = response.headers["Cache-Control"]
    
    # OWASP requirement: no-store prevents writing to cache
    assert "no-store" in cache_control, "Missing no-store directive"
    
    # HTTP/1.0 compatibility: Pragma header
    assert response.headers.get("Pragma") == "no-cache", "Missing Pragma: no-cache"
    
    # Explicit expiration
    assert response.headers.get("Expires") == "0", "Missing Expires: 0"


@pytest.mark.asyncio
@pytest.mark.security
async def test_auth_refresh_endpoint_prevents_caching(
    client: AsyncClient,
) -> None:
    """Token refresh endpoint MUST NOT be cached.
    
    Risk: Cached refresh tokens allow token replay attacks.
    """
    # Note: /api/v1/auth/refresh might not be implemented yet
    # This test validates the security headers middleware works if endpoint exists
    response = await client.post("/api/v1/auth/refresh")
    
    # Response may be 401/404 without valid refresh token or if endpoint doesn't exist
    assert response.status_code in [200, 401, 404]
    
    # If endpoint exists (not 404), verify anti-caching headers
    if response.status_code != 404:
        assert "Cache-Control" in response.headers
        assert "no-store" in response.headers["Cache-Control"]
        assert response.headers.get("Pragma") == "no-cache"
        assert response.headers.get("Expires") == "0"


@pytest.mark.asyncio
@pytest.mark.security
async def test_user_endpoints_prevent_caching(
    client: AsyncClient,
    superadmin_headers: dict[str, str],
) -> None:
    """User data endpoints MUST prevent caching.
    
    Risk: Cached user data exposes PII (email, roles, tenant_id) to:
    - Proxy cache administrators
    - Shared proxy users (cache poisoning)
    - Browser cache forensics
    """
    # Test GET /users/me endpoint
    response = await client.get(
        "/api/v1/users/me",
        headers=superadmin_headers,
    )
    
    assert response.status_code == 200
    
    # Verify no-store headers
    assert "Cache-Control" in response.headers
    cache_control = response.headers["Cache-Control"]
    assert "no-store" in cache_control or "private" in cache_control, \
        "User data must not be cached or only privately cached"
    
    # Test GET /users list endpoint
    response = await client.get(
        "/api/v1/users",
        headers=superadmin_headers,
    )
    
    assert response.status_code == 200
    assert "Cache-Control" in response.headers
    assert "no-store" in response.headers["Cache-Control"] or \
           "private" in response.headers["Cache-Control"]


@pytest.mark.asyncio
@pytest.mark.security
async def test_policy_endpoints_prevent_caching(
    client: AsyncClient,
    superadmin_headers: dict[str, str],
) -> None:
    """Policy endpoints MUST NOT be cached.
    
    Risk: Cached authorization policies lead to:
    - Stale access control decisions
    - Information disclosure about security rules
    - Authorization bypass via cache poisoning
    """
    # Use correct query parameter format
    response = await client.get(
        "/api/v1/policies?tenant_id=system",
        headers=superadmin_headers,
    )
    
    # Should return 200 with policies, may return 500 if database not setup
    assert response.status_code in [200, 500]
    
    # Policies are highly sensitive - must never be cached (check headers regardless of status)
    assert "Cache-Control" in response.headers
    assert "no-store" in response.headers["Cache-Control"]
    assert response.headers.get("Pragma") == "no-cache"


@pytest.mark.asyncio
@pytest.mark.security
async def test_audit_endpoints_prevent_caching(
    client: AsyncClient,
    superadmin_headers: dict[str, str],
) -> None:
    """Audit log endpoints MUST NOT be cached.
    
    Risk: Cached audit logs:
    - Expose sensitive event metadata
    - Reveal system behavior patterns
    - Contain correlation IDs for tracking
    """
    response = await client.get(
        "/api/v1/audit/events",
        headers=superadmin_headers,
    )
    
    # May be 200 with events or 200 with empty list
    assert response.status_code == 200
    
    # Audit logs are confidential
    assert "Cache-Control" in response.headers
    assert "no-store" in response.headers["Cache-Control"]


@pytest.mark.asyncio
@pytest.mark.security
async def test_tenant_endpoints_prevent_caching(
    client: AsyncClient,
    superadmin_headers: dict[str, str],
) -> None:
    """Tenant configuration endpoints MUST NOT be cached.
    
    Risk: Cached tenant data exposes:
    - Multi-tenant architecture details
    - Customer organization information
    - Tenant isolation boundaries
    """
    response = await client.get(
        "/api/v1/tenants",
        headers=superadmin_headers,
    )
    
    assert response.status_code == 200
    
    # Tenant data is sensitive business information
    assert "Cache-Control" in response.headers
    assert "no-store" in response.headers["Cache-Control"] or \
           "private" in response.headers["Cache-Control"]


@pytest.mark.asyncio
@pytest.mark.security
async def test_health_endpoint_can_be_cached(
    client: AsyncClient,
) -> None:
    """Public health check endpoint CAN be cached.
    
    This is a non-sensitive endpoint that benefits from caching
    to reduce load on health checks from monitoring systems.
    """
    # Check both /health and /api/v1/health paths
    response = await client.get("/api/v1/health")
    
    assert response.status_code == 200
    
    # Health endpoint can have any cache policy (or none)
    # This test just ensures it doesn't break
    # It's OK if Cache-Control is present or absent for public endpoints


@pytest.mark.asyncio
@pytest.mark.security
async def test_feature_flags_prevent_caching(
    client: AsyncClient,
    superadmin_headers: dict[str, str],
) -> None:
    """Feature flag endpoints MUST NOT be cached.
    
    Risk: Cached feature flags:
    - Lead to stale feature state
    - Prevent real-time feature toggles
    - Expose feature rollout strategy
    """
    # Feature flags require tenant_id parameter
    response = await client.get(
        "/api/v1/feature-flags?tenant_id=system",
        headers=superadmin_headers,
    )
    
    # May be 200, 404, 501, or 500 (database errors)
    assert response.status_code in [200, 404, 500, 501]
    
    # If endpoint returns data (200), must prevent caching
    if response.status_code == 200:
        assert "Cache-Control" in response.headers
        assert "no-store" in response.headers["Cache-Control"]
    
    # For all sensitive endpoints, Cache-Control headers should be set
    # (middleware applies to all /api/v1/* paths)
    if response.status_code in [200, 500]:  # Even errors get security headers
        assert "Cache-Control" in response.headers
        assert "no-store" in response.headers["Cache-Control"]


@pytest.mark.asyncio
@pytest.mark.security
async def test_security_headers_include_xss_protection(
    client: AsyncClient,
    superadmin_headers: dict[str, str],
) -> None:
    """All API responses should include additional security headers.
    
    Defense in depth: Beyond caching, include headers for:
    - XSS protection
    - Content type sniffing prevention
    - Clickjacking prevention
    """
    response = await client.get(
        "/api/v1/users/me",
        headers=superadmin_headers,
    )
    
    assert response.status_code == 200
    
    # Additional security headers (defense in depth)
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    
    # Frame options to prevent clickjacking
    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] in ["DENY", "SAMEORIGIN"]
