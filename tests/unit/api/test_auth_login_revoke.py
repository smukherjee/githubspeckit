"""TEST-API-13 Auth login/refresh/revoke (simplified Phase 2 scope).

Refresh token & revoke flows minimal placeholders; login must return a token structure.
"""
from fastapi.testclient import TestClient
from adapters.api.app import create_app


def test_password_login_and_revoke_flow():
    app = create_app()
    client = TestClient(app)

    # Seed a user via user creation endpoint (simplified setup)
    tr = client.post("/v1/tenants", json={"name": "AuthCorp"})
    tenant_id = tr.json()["tenant_id"]
    ur = client.post("/v1/users", json={"tenant_id": tenant_id, "email": "bob@example.com", "roles": ["standard"], "password": "Passw0rd123"})
    assert ur.status_code == 201
    user_id = ur.json()["user_id"]

    # Login
    lr = client.post("/v1/auth/login", json={"user_id": user_id, "password": "Passw0rd123"})
    assert lr.status_code == 200
    body = lr.json()
    assert body.get("access_token")
    assert body.get("token_type") == "bearer"

    # Revoke (placeholder endpoint) should 200 even if logic minimal
    rv = client.post("/v1/auth/revoke", json={"user_id": user_id})
    assert rv.status_code == 200
    assert rv.json()["revoked"] is True
