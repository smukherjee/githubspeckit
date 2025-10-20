"""TEST-API-21 Metrics endpoints contract.
Validates /metrics (Prometheus text) and /v1/metrics/snapshot JSON set.

Note: These endpoints require authentication as of V1.0 RBAC enforcement.
"""
import pytest
from fastapi.testclient import TestClient
from adapters.api.app import create_app
from auth_core.jwt import JWTService, JWTKeySet


@pytest.mark.contract
def test_metrics_endpoints_contract():
    """Test metrics endpoints with V1.0 RBAC enforcement.
    
    Both /metrics and /api/v1/metrics/snapshot now require authentication.
    """
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
    
    # Test metrics snapshot endpoint
    snap = client.get("/api/v1/metrics/snapshot", headers=headers)
    assert snap.status_code == 200
    data = snap.json()
    assert isinstance(data.get("metrics"), list)
    
    # Test raw prometheus exposition endpoint
    prom = client.get("/metrics", headers=headers)
    assert prom.status_code == 200
    assert "# HELP" in prom.text or len(prom.text) > 0
