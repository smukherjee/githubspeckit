"""TEST-API-19 Embed exchange contract.
Ensures /v1/embed/exchange accepts request body {embed_token} and returns session shape per OpenAPI.
"""
import pytest
from fastapi.testclient import TestClient
from adapters.api.app import create_app


@pytest.mark.contract
def test_embed_exchange_contract_basic():
    app = create_app()
    client = TestClient(app)
    # For now the implemented route returns {token: ..}; spec expects EmbedSession.
    # This test asserts current mismatch to drive implementation.
    resp = client.post("/v1/embed/exchange", json={"embed_token": "dummy"})
    assert resp.status_code in (200, 400)
    body = resp.json()
    # Force a failure until endpoint returns session fields
    assert "session_id" in body, "Expected session_id field per contract (failing until implemented)"
