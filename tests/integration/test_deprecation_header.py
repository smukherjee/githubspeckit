"""TEST-XCUT-05 Deprecation header contract.
Checks that /v1/feature-flags GET returns Deprecation header via middleware.
"""
from fastapi.testclient import TestClient
from adapters.api.app import create_app


def test_deprecation_header_feature_flags_list():
    app = create_app()
    client = TestClient(app)
    # seed a tenant & create a flag
    tenant = client.post("/v1/tenants", json={"name": "DeprecCorp"}).json()
    client.post("/v1/feature-flags", json={"tenant_id": tenant["tenant_id"], "key": "legacy_switch"})
    resp = client.get(f"/v1/feature-flags?tenant_id={tenant['tenant_id']}")
    assert resp.status_code == 200
    assert resp.headers.get("Deprecation") == "true"
