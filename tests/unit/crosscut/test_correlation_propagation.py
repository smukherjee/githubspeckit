from fastapi.testclient import TestClient
from adapters.api.app import create_app


def test_correlation_header_roundtrip():
    app = create_app()
    client = TestClient(app)
    # V1.0: Health endpoint is at /health (not /api/v1/health)
    resp = client.get("/health", headers={"X-Correlation-ID": "cid-test-123"})
    assert resp.status_code == 200
    # Structured log record should carry same correlation id and have trace/span IDs (may be None if no span active)
    rec = app.state.log_sink.records[-1]
    assert rec["correlation_id"] == "cid-test-123"
    assert "trace_id" in rec
    assert "span_id" in rec


def test_correlation_generated_when_absent():
    app = create_app()
    client = TestClient(app)
    # V1.0: Health endpoint is at /health (not /api/v1/health)
    resp = client.get("/health")
    assert resp.status_code == 200
    rec = app.state.log_sink.records[-1]
    assert rec["correlation_id"]  # should be non-empty placeholder or generated id
