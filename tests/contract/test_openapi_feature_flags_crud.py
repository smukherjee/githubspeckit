"""TEST-API-17 Feature Flags CRUD contract.
Ensures create/update(list) basic shape.
"""
import pytest
from fastapi.testclient import TestClient
from adapters.api.app import create_app
from uuid import uuid4


@pytest.mark.contract
def test_feature_flags_crud_basic():
    app = create_app()
    client = TestClient(app)
    tenant = client.post("/v1/tenants", json={"name": "FlagsCo"}).json()
    tenant_id = tenant["tenant_id"]
    fid = str(uuid4())
    # create flag
    create = client.post("/v1/feature-flags", json={"flag_id": fid, "tenant_id": tenant_id, "key": "beta_mode", "state": "enabled"})
    assert create.status_code == 201
    body = create.json()
    assert body["flag_id"] == fid
    assert body["state"] == "enabled"
    # list
    listing = client.get(f"/v1/feature-flags?tenant_id={tenant_id}")
    assert listing.status_code == 200
    flags = listing.json()["flags"]
    assert any(f["flag_id"] == fid for f in flags)
