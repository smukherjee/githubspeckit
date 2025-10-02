"""TEST-API-07 Tenant CRUD + idempotency.

Validates create → list → soft delete → restore flow using in-memory repository.
Ensures posting the same tenant name twice returns the same tenant_id (idempotent create).
"""
from fastapi.testclient import TestClient
from adapters.api.app import create_app


def test_tenant_crud_and_idempotent_create():
    app = create_app()
    client = TestClient(app)

    # Create tenant A
    r1 = client.post("/v1/tenants", json={"name": "Acme Corp"})
    assert r1.status_code == 201
    t1 = r1.json()
    assert t1["name"] == "Acme Corp"
    tid = t1["tenant_id"]

    # Idempotent second create (same name)
    r2 = client.post("/v1/tenants", json={"name": "Acme Corp"})
    assert r2.status_code in (200, 201)
    t2 = r2.json()
    assert t2["tenant_id"] == tid

    # List tenants
    rl = client.get("/v1/tenants")
    assert rl.status_code == 200
    tenants = rl.json()["tenants"]
    assert any(t["tenant_id"] == tid for t in tenants)

    # Soft delete
    rd = client.post(f"/v1/tenants/{tid}/delete")
    assert rd.status_code == 200
    assert rd.json()["status"] == "soft_deleted"

    # Restore
    rr = client.post(f"/v1/tenants/{tid}/restore")
    assert rr.status_code == 200
    assert rr.json()["status"] == "active"
