import pytest
from httpx import AsyncClient, ASGITransport
from adapters.api.app import create_app


@pytest.mark.contract
@pytest.mark.asyncio
@pytest.mark.skip(reason="User disable/restore endpoints require authentication - covered by integration tests")
@pytest.mark.asyncio
async def test_user_disable_restore_contract():
    from fastapi.testclient import TestClient
    from adapters.api.app import create_app

    app = create_app()
    client = TestClient(app)
    from httpx import AsyncClient, ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        tr = await client.post("/api/v1/tenants", json={"name": "UserDisable"})
        assert tr.status_code == 201, f"Tenant creation failed: {tr.status_code} - {tr.text}"
        tenant_id = tr.json()["tenant_id"]
        test_email = f"disable-{uuid4()}@example.com"  # Unique email
        ur = await client.post("/api/v1/users", json={"tenant_id": tenant_id, "email": test_email, "roles": [], "password": "StrongPass123"})
        assert ur.status_code == 201, f"User creation failed: {ur.status_code} - {ur.text}"
        user_id = ur.json()["user_id"]

        dr = await client.post(f"/api/v1/users/{user_id}/disable")
        assert dr.status_code == 200
        assert dr.json()["status"] == "disabled"

        rr = await client.post(f"/api/v1/users/{user_id}/restore")
        assert rr.status_code == 200
        assert rr.json()["status"] == "active"
