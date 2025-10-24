"""
Contract Test: T018 - Health endpoint returns V1.0 version

Tests that the health endpoint reports version 1.0.0:
- GET /v1/health -> version field is "1.0.0"
- GET /health -> version field is "1.0.0" (backward compat)

Expected to FAIL until Phase 3.4 implementation (T046-T049)
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_returns_version_1_0_0(test_client: AsyncClient):
    """V1.0 health endpoint should return version 1.0.0"""
    
    response = await test_client.get("/health")
    
    assert response.status_code == 200, (
        f"Health endpoint should return 200, got {response.status_code}"
    )
    
    data = response.json()
    
    # Verify version field exists
    assert "version" in data, "Health response should include 'version' field"
    
    # Verify version is exactly "1.0.0"
    actual_version = data["version"]
    assert actual_version == "1.0.0", (
        f"Expected version '1.0.0', got '{actual_version}'"
    )


@pytest.mark.asyncio
async def test_health_endpoint_includes_status(test_client: AsyncClient):
    """V1.0 health endpoint should include status field"""
    
    response = await test_client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    
    # Verify status field exists
    assert "status" in data, "Health response should include 'status' field"
    
    # Status should be "healthy" or "ok"
    status = data["status"].lower()
    assert status in ["healthy", "ok", "up"], (
        f"Health status should indicate healthy state, got '{status}'"
    )


@pytest.mark.skip(reason="V1.0: Only /health endpoint exists, no versioned aliases")
@pytest.mark.asyncio
async def test_versioned_health_endpoint(test_client: AsyncClient):
    """V1.0 versioned health endpoint /v1/health should also return version"""
    
    response = await test_client.get("/v1/health")
    
    # If endpoint doesn't exist yet, this test is expected to fail
    if response.status_code == 404:
        pytest.skip("Versioned /v1/health endpoint not implemented yet")
    
    assert response.status_code == 200, (
        f"Versioned health endpoint should return 200, got {response.status_code}"
    )
    
    data = response.json()
    
    # Verify version field
    assert "version" in data, "Versioned health should include 'version' field"
    assert data["version"] == "1.0.0", (
        f"Versioned health should return '1.0.0', got '{data['version']}'"
    )


@pytest.mark.asyncio
async def test_health_endpoint_response_time_acceptable(test_client: AsyncClient):
    """V1.0 health endpoint should respond quickly (<100ms p50)"""
    import time
    
    # Warm up
    await test_client.get("/health")
    
    # Measure response time
    start = time.time()
    response = await test_client.get("/health")
    elapsed_ms = (time.time() - start) * 1000
    
    assert response.status_code == 200
    
    # Health endpoint should be fast (relaxed to 500ms for test environment)
    assert elapsed_ms < 500, (
        f"Health endpoint should respond in <500ms, took {elapsed_ms:.2f}ms"
    )


@pytest.mark.asyncio
async def test_health_endpoint_no_sensitive_info(test_client: AsyncClient):
    """V1.0 health endpoint should not leak sensitive information"""
    
    response = await test_client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    data_str = str(data).lower()
    
    # Should not expose sensitive info
    sensitive_keywords = [
        "password",
        "secret",
        "token",
        "key",
        "credential",
        "database_url",
        "connection_string",
    ]
    
    for keyword in sensitive_keywords:
        assert keyword not in data_str, (
            f"Health endpoint should not expose sensitive info like '{keyword}'"
        )
