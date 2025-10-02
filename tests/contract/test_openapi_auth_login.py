import pytest
from fastapi.testclient import TestClient
from adapters.api.app import create_app


@pytest.mark.contract
def test_auth_login_success_and_error_shapes():
    app = create_app()
    client = TestClient(app)

    # create tenant and user
    tr = client.post("/v1/tenants", json={"name": "AuthLogin"})
    tenant_id = tr.json()["tenant_id"]
    ur = client.post("/v1/users", json={"tenant_id": tenant_id, "email": "login@example.com", "roles": ["standard"], "password": "StrongPass123"})
    assert ur.status_code == 201
    user_id = ur.json()["user_id"]

    # success
    lr = client.post("/v1/auth/login", json={"user_id": user_id, "password": "StrongPass123"})
    assert lr.status_code == 200
    body = lr.json()
    assert set(["access_token", "token_type", "expires_at"]) <= set(body.keys())
    assert body["token_type"] == "bearer"

    # failure (bad password)
    lf = client.post("/v1/auth/login", json={"user_id": user_id, "password": "Wrong"})
    assert lf.status_code == 401
    err = lf.json()
    # Accept either standardized envelope {error:{message}} or FastAPI detail field
    detail = err.get("detail")
    if "error" in err:
        assert err["error"].get("message") in {"internal_error", "invalid_credentials"}
    else:
        assert detail == "invalid_credentials"
