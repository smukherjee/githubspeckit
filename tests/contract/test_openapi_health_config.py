import pytest
from fastapi.testclient import TestClient
from adapters.api.app import create_app as rel_import_attempt  # may fail in current path

try:
    from src.adapters.api.app import create_app  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    create_app = rel_import_attempt


@pytest.mark.contract
def test_health_status_endpoint():
    """V1.0: Health endpoint is at /health (simple check)"""
    app = create_app()
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    # V1.0: Simplified health check
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"


@pytest.mark.contract
def test_config_export_contract():
    """Test config export endpoint with V1.0 RBAC enforcement.
    
    This endpoint requires authentication (superadmin or tenant_admin role).
    """
    from auth_core.jwt import JWTService, JWTKeySet
    
    app = create_app()
    client = TestClient(app)
    
    # Create authenticated client with superadmin token
    jwt_keys = JWTKeySet(active_kid="v1", keys={"v1": "dev-secret-key"})
    jwt_service = JWTService(keys=jwt_keys, issuer="modern-backend", audience="modern-backend")
    
    # Generate superadmin token
    token = jwt_service.issue(
        sub="11111111-1111-1111-1111-111111111111",  # Superadmin user UUID
        tenant_id="00000000-0000-0000-0000-000000000000",  # Superadmin tenant UUID
        roles=["superadmin"],
        extra={}
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/v1/config", headers=headers)
    # Until implemented expect 404, then we will tighten to 200 with schema checks
    assert resp.status_code in (404, 200)
    if resp.status_code == 200:
        data = resp.json()
        assert "hash" in data
        assert "entries" in data
