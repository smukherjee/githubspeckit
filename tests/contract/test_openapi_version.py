"""
Contract Test: T017 - OpenAPI version is 1.0.0

Tests that the OpenAPI specification declares version 1.0.0:
- GET /openapi.json -> info.version == "1.0.0"

Expected to FAIL until Phase 3.4 implementation (T046-T049)
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_openapi_version_is_v1_0_0(test_client: AsyncClient):
    """V1.0 OpenAPI spec should declare version 1.0.0"""
    
    response = await test_client.get("/openapi.json")
    
    assert response.status_code == 200, (
        f"OpenAPI endpoint should return 200, got {response.status_code}"
    )
    
    spec = response.json()
    
    # Verify info section exists
    assert "info" in spec, "OpenAPI spec should have 'info' section"
    
    # Verify version field exists
    assert "version" in spec["info"], "OpenAPI spec info should have 'version' field"
    
    # Verify version is exactly "1.0.0"
    actual_version = spec["info"]["version"]
    assert actual_version == "1.0.0", (
        f"Expected OpenAPI version '1.0.0', got '{actual_version}'"
    )


@pytest.mark.asyncio
async def test_openapi_title_indicates_v1(test_client: AsyncClient):
    """V1.0 OpenAPI spec title should indicate V1.0"""
    
    response = await test_client.get("/openapi.json")
    assert response.status_code == 200
    
    spec = response.json()
    
    # Verify title exists and mentions the API
    assert "info" in spec
    assert "title" in spec["info"]
    
    title = spec["info"]["title"]
    assert len(title) > 0, "OpenAPI spec should have a non-empty title"
    
    # Title should be descriptive (basic check)
    assert "api" in title.lower() or "backend" in title.lower(), (
        f"OpenAPI title should describe the API: {title}"
    )


@pytest.mark.asyncio
async def test_openapi_has_breaking_changes_description(test_client: AsyncClient):
    """V1.0 OpenAPI spec should document breaking changes"""
    
    response = await test_client.get("/openapi.json")
    assert response.status_code == 200
    
    spec = response.json()
    
    # Verify description field exists
    assert "info" in spec
    assert "description" in spec["info"], (
        "OpenAPI spec should have a description field documenting breaking changes"
    )
    
    description = spec["info"]["description"]
    assert len(description) > 0, "OpenAPI description should not be empty"
    
    # Description should mention V1.0 or breaking changes
    description_lower = description.lower()
    assert "v1.0" in description_lower or "1.0" in description_lower or "breaking" in description_lower, (
        f"OpenAPI description should mention V1.0 or breaking changes: {description[:100]}..."
    )


@pytest.mark.asyncio
async def test_openapi_spec_valid_json_structure(test_client: AsyncClient):
    """V1.0 OpenAPI spec should be valid JSON with required top-level fields"""
    
    response = await test_client.get("/openapi.json")
    assert response.status_code == 200
    
    spec = response.json()
    
    # Verify OpenAPI 3.x structure
    assert "openapi" in spec, "Should have 'openapi' version field"
    assert spec["openapi"].startswith("3."), (
        f"Should be OpenAPI 3.x, got {spec['openapi']}"
    )
    
    # Verify required top-level fields
    required_fields = ["info", "paths"]
    for field in required_fields:
        assert field in spec, f"OpenAPI spec should have '{field}' field"
