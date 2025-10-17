"""TEST-API-09 User list & restore.

Covers listing users by tenant, soft deleting (disable) and restoring.

NOTE: This test is now covered by integration tests with proper authentication.
"""
import pytest
from fastapi.testclient import TestClient
from adapters.api.app import create_app
from uuid import uuid4


@pytest.mark.skip(reason="Now covered by integration tests with authentication and correct endpoints")
def test_user_list_and_restore_flow():
    app = create_app()
    client = TestClient(app)

    # Create tenant first
    tr = client.post("/api/v1/tenants", json={"name": "Umbrella"})
    assert tr.status_code in (200, 201)
    tenant_id = tr.json()["tenant_id"]

    # Create user (temporary endpoint to be implemented) - expect 201
    ur = client.post("/api/v1/users", json={"tenant_id": tenant_id, "email": "alice@example.com", "roles": ["standard"]})
    assert ur.status_code == 201
    user_id = ur.json()["user_id"]

    # List users
    lr = client.get(f"/api/v1/users?tenant_id={tenant_id}")
    assert lr.status_code == 200
    users = lr.json()["users"]
    assert any(u["user_id"] == user_id for u in users)

    # Disable user
    dr = client.post(f"/api/v1/users/{user_id}/disable")
    assert dr.status_code == 200
    assert dr.json()["status"] == "disabled"

    # Restore user
    rr = client.post(f"/api/v1/users/{user_id}/restore")
    assert rr.status_code == 200
    assert rr.json()["status"] == "active"
