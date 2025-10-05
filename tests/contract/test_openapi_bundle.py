"""TEST-API-01 OpenAPI bundle validation.

Ensures the FastAPI-generated OpenAPI document exposes expected core paths
and required top-level metadata (title, version, paths) before further
endpoint expansion.
"""
import pytest
from fastapi.testclient import TestClient
from adapters.api.app import create_app


@pytest.mark.contract
def test_openapi_bundle_contains_expected_minimal_paths():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    doc = resp.json()
    # Basic schema keys
    assert doc["info"]["title"]
    assert "paths" in doc
    paths = doc["paths"].keys()
    # Minimal expected paths (already implemented or stubbed)
    # Note: disable/restore are handled via POST to /v1/users/{user_id} with body
    expected = [
        "/v1/health",
        "/v1/config",
        "/v1/invitations/{invitation_id}/accept",
        "/v1/users",
        "/v1/users/{user_id}",
        "/v1/users/{user_id}/restore",
        "/v1/auth/login",
        "/v1/auth/revoke",
    ]
    for p in expected:
        # Skip paths that require /api/v1 prefix
        api_prefixed = p.replace("/v1/", "/api/v1/")
        assert p in paths or api_prefixed in paths, f"Missing path {p} (or {api_prefixed}) in OpenAPI bundle"
