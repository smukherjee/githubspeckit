from adapters.api.app import create_app
from fastapi.testclient import TestClient

def test_justification_registry_metrics():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/metrics/snapshot")
    names = set(resp.json()["metrics"])
    # Ensure custom quality metrics appear (value may be zero)
    assert "justifications_count" in names
