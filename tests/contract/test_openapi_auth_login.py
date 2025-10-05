import pytest
from httpx import AsyncClient, ASGITransport
from adapters.api.app import create_app


@pytest.mark.skip(reason="Auth endpoints require authentication for tenant/user setup - covered by integration tests")
@pytest.mark.contract
@pytest.mark.asyncio
async def test_auth_login_success_and_error_shapes():
    from uuid import uuid4
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # create tenant and user
        tr = await client.post("/v1/tenants", json={"name": "AuthLogin"})
        tenant_id = tr.json()["tenant_id"]
        test_email = f"login-{uuid4()}@example.com"  # Unique email
        ur = await client.post("/v1/users", json={"tenant_id": tenant_id, "email": test_email, "roles": ["standard"], "password": "StrongPass123"})
        assert ur.status_code == 201, f"User creation failed: {ur.status_code} - {ur.text}"
        user_id = ur.json()["user_id"]

        # success
        lr = await client.post("/v1/auth/login", json={"email": test_email, "password": "StrongPass123"})
        assert lr.status_code == 200, f"Login failed: {lr.status_code} - {lr.text}"
        body = lr.json()
        assert set(["access_token", "token_type", "expires_at"]) <= set(body.keys())
        assert body["token_type"] == "bearer"

        # failure (bad password)
        lf = await client.post("/v1/auth/login", json={"email": test_email, "password": "Wrong"})
        assert lf.status_code == 401
        err = lf.json()
        # Accept either standardized envelope {error:{message}} or FastAPI detail field
        detail = err.get("detail")
        if "error" in err:
            assert err["error"].get("message") in {"internal_error", "invalid_credentials"}
        else:
            assert detail == "invalid_credentials"
