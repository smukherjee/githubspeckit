"""TEST-API-21 Metrics endpoints contract.
Validates /metrics (Prometheus text) and /v1/metrics/snapshot JSON set.
"""
import pytest
from fastapi.testclient import TestClient
from adapters.api.app import create_app


@pytest.mark.contract
def test_metrics_endpoints_contract():
    app = create_app()
    client = TestClient(app)
    # snapshot
    snap = client.get("/api/v1/metrics/snapshot")
    assert snap.status_code == 200
    data = snap.json()
    assert isinstance(data.get("metrics"), list)
    # raw prometheus exposition
    prom = client.get("/metrics")
    assert prom.status_code == 200
    assert "# HELP" in prom.text or len(prom.text) > 0
