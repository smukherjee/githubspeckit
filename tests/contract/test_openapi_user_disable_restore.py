import pytest
from fastapi.testclient import TestClient
from adapters.api.app import create_app


@pytest.mark.contract
def test_user_disable_restore_contract():
    app = create_app()
    client = TestClient(app)
    tr = client.post("/v1/tenants", json={"name": "UserDisable"})
    tenant_id = tr.json()["tenant_id"]
    ur = client.post("/v1/users", json={"tenant_id": tenant_id, "email": "disable@example.com", "roles": [], "password": "StrongPass123"})
    user_id = ur.json()["user_id"]

    dr = client.post(f"/v1/users/{user_id}/disable")
    assert dr.status_code == 200
    assert dr.json()["status"] == "disabled"

    rr = client.post(f"/v1/users/{user_id}/restore")
    assert rr.status_code == 200
    assert rr.json()["status"] == "active"
