"""TEST-API-28 Config error report JSON schema contract.
Will call /v1/config/errors and expect structured list of errors with code/message/path.
"""
import pytest
from fastapi.testclient import TestClient
from adapters.api.app import create_app


@pytest.mark.contract
def test_config_error_report_contract():
    app = create_app()
    client = TestClient(app)
    r = client.get("/v1/config/errors")
    assert r.status_code == 200, f"Expected 200 OK for config error report endpoint, got {r.status_code}"
    data = r.json()
    assert "errors" in data and isinstance(data["errors"], list)
    # Each error item minimal shape; current implementation returns empty list until errors exist.
    for item in data["errors"]:
        assert {"code", "message", "path"}.issubset(item.keys())
