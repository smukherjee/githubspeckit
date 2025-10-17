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
        "/api/v1/health",
        "/api/v1/config",
        "/api/v1/invitations/{invitation_id}/accept",
        "/api/v1/users",
        "/api/v1/users/{user_id}",
        "/api/v1/users/{user_id}/restore",
        "/api/v1/auth/login",
        "/api/v1/auth/revoke",
    ]
    for p in expected:
        assert p in paths, f"Missing path {p} in OpenAPI bundle"
