from adapters.api.app import create_app
from fastapi.testclient import TestClient

def test_quality_metrics_failure_counter():
    app = create_app()
    qm = app.state.quality_metrics
    # simulate a failure
    qm.record_gate_failure()
    client = TestClient(app)
    prom_text = client.get("/metrics").text
    assert "quality_gates_fail_total" in prom_text
