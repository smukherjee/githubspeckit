from fastapi.testclient import TestClient
from adapters.api.app import create_app
from fastapi import APIRouter, HTTPException

def test_failed_token_validation_logging():
    app = create_app()
    r = APIRouter()
    @r.get("/auth/validate")
    async def validate():  # pragma: no cover
        # Simulate token validation failure by raising
        raise HTTPException(status_code=401, detail="invalid_token")
    app.include_router(r)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/auth/validate", headers={"Authorization": "Bearer bad", "X-Correlation-ID": "cid-val"})
    assert resp.status_code in {401,500}  # middleware converts only generic exceptions; HTTPException passes through
    # Ensure a log record emitted with correlation id
    rec = app.state.log_sink.records[-1]
    assert rec["correlation_id"] == "cid-val"
