from fastapi.testclient import TestClient
from adapters.api.app import create_app
from fastapi import APIRouter

def test_error_envelope_schema():
    app = create_app()
    r = APIRouter()
    @r.get("/api/v1/test/err")  # Use /api/v1 prefix
    async def err():  # pragma: no cover
        raise RuntimeError("boom secret")
    app.include_router(r)
    client = TestClient(app, raise_server_exceptions=False)
    
    # Create a valid JWT for testing
    from adapters.api.deps import get_jwt_service
    from uuid import uuid4
    
    jwt_svc = get_jwt_service()
    token = jwt_svc.issue(
        sub=str(uuid4()),
        tenant_id=str(uuid4()),
        roles=["user"],
        extra={}
    )
    
    resp = client.get(
        "/api/v1/test/err",
        headers={
            "X-Correlation-ID": "cid-sec",
            "Authorization": f"Bearer {token}"
        }
    )
    assert resp.status_code == 500
    body = resp.json()
    assert "error" in body
    e = body["error"]
    assert e["code"] in {"RuntimeError"}
    assert e["message"] == "internal_error"
    assert e["correlation_id"] == "cid-sec"
