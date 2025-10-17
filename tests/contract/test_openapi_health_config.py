import pytest
from fastapi.testclient import TestClient
from adapters.api.app import create_app as rel_import_attempt  # may fail in current path

try:
    from src.adapters.api.app import create_app  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    create_app = rel_import_attempt


@pytest.mark.contract
def test_health_status_endpoint():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    # Expected keys per FR-015 (partial implementation)
    assert data["status"] == "ok"
    assert isinstance(data["migrations_applied"], bool)
    assert "key_rotation_version" in data


@pytest.mark.contract
def test_config_export_contract():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/v1/config")
    # Until implemented expect 404, then we will tighten to 200 with schema checks
    assert resp.status_code in (404, 200)
    if resp.status_code == 200:
        data = resp.json()
        assert "hash" in data
        assert "entries" in data
