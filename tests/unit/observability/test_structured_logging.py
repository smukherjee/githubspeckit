import pytest


def test_structured_logging_fields_and_redaction():
    from fastapi.testclient import TestClient
    from adapters.api.app import create_app

    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)

    # Make a request with sensitive headers
    resp = client.get(
        "/api/v1/health",
        headers={
            "X-Tenant-ID": "tenant-123",
            "Authorization": "Bearer secret-token",
            "X-Correlation-ID": "corr-abc",
        },
    )
    assert resp.status_code == 200

    # Inspect log sink
    records = app.state.log_sink.records
    assert records, "expected at least one log record"
    rec = records[-1]
    # Field presence
    for f in [
        "ts",
        "level",
        "msg",
        "http_method",
        "path",
        "status_code",
        "duration_ms",
        "tenant_id",
        "correlation_id",
        "headers",
        "had_redaction",
    ]:
        assert f in rec, f"missing field {f}"
    # Redaction enforcement: authorization header must be redacted
    assert rec["headers"]["authorization"] == "REDACTED"
    assert rec["had_redaction"] is True
    # Tenant/correlation recorded
    assert rec["tenant_id"] == "tenant-123"
    assert rec["correlation_id"] == "corr-abc"


def test_error_envelope_handler():
    from fastapi import APIRouter
    from fastapi.testclient import TestClient
    from adapters.api.app import create_app

    app = create_app()
    r = APIRouter()

    @r.get("/boom")
    async def boom():  # pragma: no cover - simple raise
        raise RuntimeError("secret internal message")

    app.include_router(r)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.get("/boom", headers={"X-Correlation-ID": "cid-1"})
    # Unified exception handler should convert to 500
    assert resp.status_code == 500
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] in {"RuntimeError"}
    # message intentionally generic
    assert body["error"]["message"] == "internal_error"
    assert body["error"]["correlation_id"] == "cid-1"
