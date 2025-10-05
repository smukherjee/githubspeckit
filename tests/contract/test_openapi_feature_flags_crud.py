"""TEST-API-17 Feature Flags CRUD contract.
Ensures create/update(list) basic shape.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from adapters.api.app import create_app
from uuid import uuid4


@pytest.mark.contract
@pytest.mark.asyncio
@pytest.mark.skip(reason="Feature flags endpoints require authentication - covered by integration tests")
@pytest.mark.asyncio
async def test_feature_flags_crud_basic():
    from fastapi.testclient import TestClient
    from adapters.api.app import create_app

    app = create_app()
    client = TestClient(app)
    from httpx import AsyncClient, ASGITransport
    transport = ASGITransport(app=app)
    from uuid import uuid4

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Use unique tenant name to avoid conflicts with other tests
        unique_name = f"FlagsCo-{uuid4()}"
        tr = await client.post("/v1/tenants", json={"name": unique_name})
        assert tr.status_code == 201, f"Tenant creation failed: {tr.status_code} - {tr.text}"
        tenant = tr.json()
        tenant_id = tenant["tenant_id"]
        fid = str(uuid4())
        # create flag with unique key to avoid conflicts
        unique_key = f"beta_mode_{uuid4()}"
        create = await client.post("/v1/feature-flags", json={"flag_id": fid, "tenant_id": tenant_id, "key": unique_key, "state": "enabled"})
        assert create.status_code == 201, f"Feature flag creation failed: {create.status_code} - {create.text}"
        body = create.json()
        assert body["flag_id"] == fid
        assert body["state"] == "enabled"
        # list
        listing = await client.get(f"/v1/feature-flags?tenant_id={tenant_id}")
        assert listing.status_code == 200
        flags = listing.json()["flags"]
        assert any(f["flag_id"] == fid for f in flags)
