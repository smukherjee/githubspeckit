"""TEST-API-15 / TEST-API-15A Policy dry-run contract tests.

Validates dry-run endpoint response shape and rationale enumeration guard.
"""
import pytest
from fastapi.testclient import TestClient
from adapters.api.app import create_app

# V1.0: Policy engine deferred to Phase 2 (spec 014)
pytestmark = pytest.mark.skip(reason="Deferred to Phase 2: Policy engine - spec 014")


@pytest.mark.contract
def test_policy_dry_run_success_allows_basic_shape(superadmin_headers):
    """Policy dry-run requires authentication - using superadmin credentials."""
    app = create_app()
    client = TestClient(app)
    payload = {"tenant_id": "t1", "action": "read_resource", "resource_type": "doc", "attributes": {}}
    r = client.post("/api/v1/policies/dry-run", json=payload, headers=superadmin_headers)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["decision"] in {"ALLOW", "DENY", "ABSTAIN"}
    assert isinstance(body.get("rationales"), list)
    # Each rationale is expected code-style string
    for rat in body["rationales"]:
        assert isinstance(rat, str)


@pytest.mark.contract
def test_policy_dry_run_unknown_rationale_rejected(superadmin_headers):
    """Policy dry-run requires authentication - using superadmin credentials."""
    app = create_app()
    client = TestClient(app)
    # trigger an action purposely generating unknown rationale code
    payload = {"tenant_id": "t1", "action": "trigger_unknown", "resource_type": "doc", "attributes": {}}
    r = client.post("/api/v1/policies/dry-run", json=payload, headers=superadmin_headers)
    # Expect 400 enumeration guard
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("detail") == "unknown_rationale_code"
