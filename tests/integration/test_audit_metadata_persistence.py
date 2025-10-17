"""TEST-XCUT-03 Audit metadata persistence.
Ensures created_by/updated_by fields are populated through middleware/service hooks.
Currently failing until population logic is implemented.
"""
import pytest
from fastapi.testclient import TestClient
from adapters.api.app import create_app


@pytest.mark.skip(reason="Audit metadata (created_by/updated_by) implementation deferred to Phase 2")
def test_audit_metadata_population_placeholder():
    app = create_app()
    client = TestClient(app)
    t = client.post("/api/v1/tenants", json={"name": "MetaCorp"}).json()
    assert t.get("created_by"), "Expected created_by populated (failing until implemented)"