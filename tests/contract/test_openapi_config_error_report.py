"""TEST-API-28 Config error report JSON schema contract.
Will call /v1/config/errors and expect structured list of errors with code/message/path.

Note: This endpoint requires authentication as of V1.0 RBAC enforcement.
Only superadmin or tenant_admin roles can access configuration endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from adapters.api.app import create_app
from auth_core.jwt import JWTService, JWTKeySet


@pytest.mark.contract
def test_config_error_report_contract():
    app = create_app()
    client = TestClient(app)
    
    # Create authenticated client with superadmin token
    # Use the same JWT configuration as the app's get_jwt_service() in deps.py
    jwt_keys = JWTKeySet(active_kid="v1", keys={"v1": "dev-secret-key"})
    jwt_service = JWTService(keys=jwt_keys, issuer="modern-backend", audience="modern-backend")
    
    # Generate superadmin token (using valid UUID format for user_id)
    token = jwt_service.issue(
        sub="11111111-1111-1111-1111-111111111111",  # Superadmin user UUID
        tenant_id="00000000-0000-0000-0000-000000000000",  # Superadmin tenant UUID
        roles=["superadmin"],
        extra={}
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/config/errors", headers=headers)
    assert r.status_code == 200, f"Expected 200 OK for config error report endpoint, got {r.status_code}"
    data = r.json()
    assert "errors" in data and isinstance(data["errors"], list)
    # Each error item minimal shape; current implementation returns empty list until errors exist.
    for item in data["errors"]:
        assert {"code", "message", "path"}.issubset(item.keys())
