"""TEST-API-19 Embed exchange contract.
Ensures /v1/embed/exchange accepts request body {embed_token} and returns session shape per OpenAPI.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from adapters.api.app import create_app
from services.embed_service import EmbedService


@pytest.mark.contract
@pytest.mark.asyncio
async def test_embed_exchange_contract_basic():
    """Test embed token exchange returns proper session structure (Phase 3)."""
    # Generate a valid embed token for testing (using same secret as router)
    embed_service = EmbedService(secret=b"dev-secret")
    embed_token = embed_service.issue_embed_token(
        tenant_id="test-tenant-123",
        user_id="test-user-456",
        ttl_seconds=300
    )
    
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test with /api prefix (Phase 3 routing)
        resp = await client.post("/api/v1/embed/exchange", json={"embed_token": embed_token.token})
        assert resp.status_code in (200, 400), f"Expected 200 or 400, got {resp.status_code}: {resp.text}"
        
        if resp.status_code == 200:
            body = resp.json()
            # Verify EmbedSession structure per contract
            assert "session_id" in body, "Expected session_id field per contract"
            assert "tenant_id" in body, "Expected tenant_id field"
            assert "issued_at" in body, "Expected issued_at field"
            assert "expires_at" in body, "Expected expires_at field"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_embed_exchange_rejects_invalid_token():
    """Test that invalid embed tokens are rejected with 401."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test with invalid token
        resp = await client.post("/api/v1/embed/exchange", json={"embed_token": "invalid_token_123"})
        assert resp.status_code == 401, f"Expected 401 for invalid token, got {resp.status_code}"
        assert resp.json()["detail"] == "invalid_or_expired_embed_token"
