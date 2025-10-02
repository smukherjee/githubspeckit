from fastapi.testclient import TestClient
from adapters.api.app import create_app
from fastapi import APIRouter

def test_error_envelope_schema():
    app = create_app()
    r = APIRouter()
    @r.get("/err")
    async def err():  # pragma: no cover
        raise RuntimeError("boom secret")
    app.include_router(r)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/err", headers={"X-Correlation-ID": "cid-sec"})
    assert resp.status_code == 500
    body = resp.json()
    assert "error" in body
    e = body["error"]
    assert e["code"] in {"RuntimeError"}
    assert e["message"] == "internal_error"
    assert e["correlation_id"] == "cid-sec"
