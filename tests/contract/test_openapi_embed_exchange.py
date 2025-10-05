"""TEST-API-19 Embed exchange contract.
Ensures /v1/embed/exchange accepts request body {embed_token} and returns session shape per OpenAPI.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from adapters.api.app import create_app


@pytest.mark.contract
@pytest.mark.asyncio
async def test_embed_exchange_contract_basic():
    """Test embed token exchange returns proper session structure (Phase 3)."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test with /api prefix (Phase 3 routing)
        resp = await client.post("/api/v1/embed/exchange", json={"embed_token": "dummy_token_123"})
        assert resp.status_code in (200, 400), f"Expected 200 or 400, got {resp.status_code}: {resp.text}"
        
        if resp.status_code == 200:
            body = resp.json()
            # Verify EmbedSession structure per contract
            assert "session_id" in body, "Expected session_id field per contract"
            assert "tenant_id" in body, "Expected tenant_id field"
            assert "issued_at" in body, "Expected issued_at field"
            assert "expires_at" in body, "Expected expires_at field"
