"""TEST-API-27 Policy registration endpoint contract.
Expects POST /v1/policies/register to accept basic policy fields and return persisted policy.
"""
import pytest
from fastapi.testclient import TestClient
from adapters.api.app import create_app
from uuid import uuid4


@pytest.mark.contract
def test_policy_registration_requires_implementation():
    app = create_app()
    client = TestClient(app)
    payload = {
        "resource_type": "doc",
        "effect": "ALLOW",
        "condition_expression": "attr.owner == user.id",
        "version": 1,
        "policy_id": str(uuid4()),
    }
    r = client.post("/v1/policies/register", json=payload)
    # Expect 404 until implemented
    assert r.status_code == 201, f"Expected 201 created for policy registration, got {r.status_code} body={r.text}"
