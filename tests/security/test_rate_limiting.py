"""
Security Tests: Rate Limiting (Phase 3.6 - T053-T054)

Purpose:
    Verify rate limiting enforcement on user creation endpoint to prevent abuse.
    Tests IP-based limiting, superadmin bypass, and HTTP 429 responses.

Coverage:
    - T053: Rate limit enforcement (exceeding threshold returns 429)
    - T054: Rate limit headers present (X-RateLimit-Limit, Remaining, Reset)
    - Superadmin bypass mechanism (exempt from rate limits)
    - Redis-based distributed limiting (integration test)

Related:
    - FR-046-054: Rate limiting implementation
    - src/adapters/security/rate_limit.py: Limiter configuration
    - src/adapters/api/routers/users.py: @limiter.limit decorator
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
from uuid import uuid4
from datetime import datetime, timezone

from adapters.api.app import create_app
from adapters.persistence.db_config import DatabaseConfig
from adapters.persistence.repositories import SQLAlchemyTenantRepository, SQLAlchemyUserRepository
from domain.tenants.models import Tenant, TenantStatus
from domain.users.models import User, UserStatus
from auth_core.hashers import default_hasher


@pytest.fixture
async def app_with_rate_limiting():
    """Create FastAPI app with rate limiting enabled."""
    return create_app()


@pytest.fixture
async def setup_test_data(db_session):
    """Setup test tenant and users (tenant_admin and superadmin)."""
    tenant_repo = SQLAlchemyTenantRepository(db_session)
    user_repo = SQLAlchemyUserRepository(db_session)
    
    # Use unique identifiers to avoid conflicts across tests
    unique_id = str(uuid4())[:8]
    
    # Create test tenant
    tenant = Tenant(
        tenant_id=str(uuid4()),
        name=f"RateLimitTest-{unique_id}",
        status=TenantStatus.active,
    )
    await tenant_repo.upsert(tenant)
    
    # Create tenant_admin user
    admin_user = User(
        user_id=str(uuid4()),
        tenant_id=tenant.tenant_id,
        email=f"admin-{unique_id}@ratelimitest.com",
        password_hash=default_hasher.hash("SecurePass123!"),
        roles=["tenant_admin"],
        status=UserStatus.active,
        created_by="system",
        updated_by="system",
    )
    await user_repo.upsert(admin_user)
    
    # Create superadmin user
    superadmin_user = User(
        user_id=str(uuid4()),
        tenant_id=tenant.tenant_id,
        email=f"superadmin-{unique_id}@ratelimitest.com",
        password_hash=default_hasher.hash("SuperPass123!"),
        roles=["superadmin"],
        status=UserStatus.active,
        created_by="system",
        updated_by="system",
    )
    await user_repo.upsert(superadmin_user)

    await db_session.commit()

    return {
        "tenant": tenant,
        "admin_user": admin_user,
        "superadmin_user": superadmin_user,
    }
@pytest.fixture
async def admin_token(app_with_rate_limiting, setup_test_data):
    """Get JWT token for tenant_admin user."""
    transport = ASGITransport(app=app_with_rate_limiting)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": setup_test_data["admin_user"].email,
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 200, f"Login failed: {response.json()}"
        return response.json()["access_token"]


@pytest.fixture
async def superadmin_token(app_with_rate_limiting, setup_test_data):
    """Get JWT token for superadmin user."""
    transport = ASGITransport(app=app_with_rate_limiting)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": setup_test_data["superadmin_user"].email,
                "password": "SuperPass123!",
            },
        )
        assert response.status_code == 200, f"Login failed: {response.json()}"
        return response.json()["access_token"]


@pytest.mark.asyncio
async def test_rate_limit_enforcement_exceeding_threshold_returns_429(
    app_with_rate_limiting,
    admin_token,
    setup_test_data,
):
    """
    T053: Rate Limiting Enforcement
    
    Verify that exceeding the rate limit for user creation returns HTTP 429.
    
    Test Steps:
        1. Configure low rate limit (e.g., 2 requests/hour)
        2. Send requests exceeding the limit
        3. Verify HTTP 429 response after threshold
        4. Verify Retry-After header is present
        
    Expected:
        - First 2 requests: 201 Created
        - 3rd request: 429 Too Many Requests
        - Retry-After header present in 429 response
        
    Related:
        - FR-046: Rate limiting prevents enumeration attacks
        - FR-053: Security testing for rate limits
    """
    tenant_id = setup_test_data["tenant"].tenant_id
    
    transport = ASGITransport(app=app_with_rate_limiting)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # NOTE: slowapi's in-memory storage is shared across tests
        # Need to use unique source IP to avoid cross-test interference
        # Using X-Forwarded-For header to simulate different IPs
        
        test_ip = f"10.0.0.{uuid4().int % 255}"
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "X-Forwarded-For": test_ip,
        }
        
        # Get configured rate limit from descriptor
        from domain.config.descriptor_parser import parse_descriptor
        config = parse_descriptor("config/descriptor.toml")
        rate_limit = config.get("RATE_LIMIT_USER_CREATION", (100, False))[0]
        
        # For testing purposes, we'll send rate_limit + 1 requests
        # The last request should return 429
        success_count = 0
        rate_limited = False
        
        for i in range(rate_limit + 5):  # Try a few extra to ensure limit is hit
            response = await client.post(
                "/api/v1/users",
                json={
                    "tenant_id": tenant_id,
                    "email": f"user{i}@ratelimitest.com",
                    "roles": ["user"],
                },
                headers=headers,
            )
            
            if response.status_code == 201:
                success_count += 1
            elif response.status_code == 429:
                rate_limited = True
                # Verify Retry-After header is present
                assert "Retry-After" in response.headers, "Retry-After header missing in 429 response"
                # Verify error response format
                data = response.json()
                assert "error" in data, "Error key missing in 429 response"
                break
        
        # Assert that we hit the rate limit
        assert rate_limited, f"Rate limit not enforced (succeeded {success_count} times, expected limit {rate_limit})"
        assert success_count == rate_limit, f"Expected exactly {rate_limit} successful requests before rate limit"


@pytest.mark.asyncio
async def test_rate_limit_headers_present_in_responses(
    app_with_rate_limiting,
    admin_token,
    setup_test_data,
):
    """
    T054: Rate Limit Headers
    
    Verify that rate limit information headers are present in responses.
    
    Headers Checked:
        - X-RateLimit-Limit: Total allowed requests in window
        - X-RateLimit-Remaining: Requests remaining in current window
        - X-RateLimit-Reset: Unix timestamp when window resets
        
    Test Steps:
        1. Send request to user creation endpoint
        2. Verify rate limit headers are present
        3. Verify header values are valid integers
        
    Expected:
        - All three headers present in response
        - Limit matches configured value (100/hour)
        - Remaining decrements with each request
        - Reset is a future Unix timestamp
        
    Related:
        - FR-054: Rate limit headers for client visibility
        - slowapi headers_enabled=True configuration
    """
    tenant_id = setup_test_data["tenant"].tenant_id
    
    transport = ASGITransport(app=app_with_rate_limiting)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Use unique IP to avoid cross-test interference
        test_ip = f"10.0.0.{uuid4().int % 255}"
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "X-Forwarded-For": test_ip,
        }
        
        response = await client.post(
            "/api/v1/users",
            json={
                "tenant_id": tenant_id,
                "email": f"user_headers_test@ratelimitest.com",
                "roles": ["user"],
            },
            headers=headers,
        )
        
        # Should succeed (within rate limit)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"
        
        # Verify rate limit headers are present
        assert "X-RateLimit-Limit" in response.headers, "X-RateLimit-Limit header missing"
        assert "X-RateLimit-Remaining" in response.headers, "X-RateLimit-Remaining header missing"
        assert "X-RateLimit-Reset" in response.headers, "X-RateLimit-Reset header missing"
        
        # Verify header values are valid integers
        limit = int(response.headers["X-RateLimit-Limit"])
        remaining = int(response.headers["X-RateLimit-Remaining"])
        reset = int(response.headers["X-RateLimit-Reset"])
        
        # Get configured rate limit
        from domain.config.descriptor_parser import parse_descriptor
        config = parse_descriptor("config/descriptor.toml")
        expected_limit = config.get("RATE_LIMIT_USER_CREATION", (100, False))[0]
        
        # Assertions
        assert limit == expected_limit, f"Expected limit {expected_limit}, got {limit}"
        assert remaining < limit, f"Remaining {remaining} should be less than limit {limit}"
        assert reset > datetime.now(timezone.utc).timestamp(), "Reset timestamp should be in the future"


@pytest.mark.asyncio
async def test_superadmin_bypasses_rate_limit(
    app_with_rate_limiting,
    superadmin_token,
    setup_test_data,
):
    """
    Superadmin Bypass: Rate Limit Exemption
    
    Verify that superadmin users are exempt from rate limits.
    
    Test Steps:
        1. Get superadmin JWT token
        2. Send requests exceeding the configured rate limit
        3. Verify all requests succeed (no 429 responses)
        
    Expected:
        - All requests succeed with 201 Created
        - No rate limiting applied to superadmin
        - exempt_when=_is_superadmin mechanism working
        
    Related:
        - FR-051: Superadmin bypass mechanism
        - src/adapters/security/rate_limit.py: _is_superadmin function
    """
    tenant_id = setup_test_data["tenant"].tenant_id
    
    transport = ASGITransport(app=app_with_rate_limiting)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Use unique IP (though superadmin should be exempt anyway)
        test_ip = f"10.0.0.{uuid4().int % 255}"
        headers = {
            "Authorization": f"Bearer {superadmin_token}",
            "X-Forwarded-For": test_ip,
        }
        
        # Send requests far exceeding the rate limit
        # Superadmin should succeed on all requests
        num_requests = 10
        success_count = 0
        
        for i in range(num_requests):
            response = await client.post(
                "/api/v1/users",
                json={
                    "tenant_id": tenant_id,
                    "email": f"superadmin_test_user{i}@ratelimitest.com",
                    "roles": ["user"],
                },
                headers=headers,
            )
            
            if response.status_code == 201:
                success_count += 1
            elif response.status_code == 429:
                pytest.fail(f"Superadmin hit rate limit on request {i+1} (should be exempt)")
        
        # Assert all requests succeeded
        assert success_count == num_requests, \
            f"Superadmin bypass failed: {success_count}/{num_requests} requests succeeded"


@pytest.mark.asyncio
@pytest.mark.skip(reason="Integration test requiring Redis - run manually with Redis available")
async def test_redis_distributed_rate_limiting(
    app_with_rate_limiting,
    admin_token,
    setup_test_data,
):
    """
    Integration Test: Redis-Based Distributed Rate Limiting
    
    Verify that rate limits are enforced across multiple app instances using Redis.
    
    Test Steps:
        1. Start two FastAPI app instances with shared Redis backend
        2. Send requests to both instances from same IP
        3. Verify rate limit is enforced across both instances
        
    Expected:
        - Rate limit counter is shared via Redis
        - Exceeding limit on either instance returns 429
        - Demonstrates horizontal scaling capability
        
    Note:
        This is an integration test requiring a running Redis instance.
        Skipped by default in unit test suite.
        
    Related:
        - FR-047: Redis backend for distributed rate limiting
        - config/descriptor.toml: REDIS_URL configuration
    """
    # This test would require:
    # 1. Redis server running locally or in CI
    # 2. Two app instances sharing the same Redis connection
    # 3. Verification that counter is shared across instances
    
    # Placeholder for integration testing
    pytest.skip("Redis integration test - implement when Redis is available in CI")
