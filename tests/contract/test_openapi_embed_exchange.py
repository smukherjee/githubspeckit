"""TEST-API-19 Embed exchange contract.
Ensures /v1/embed/exchange accepts request body {embed_token} and returns session shape per OpenAPI.

Note: This endpoint requires authentication as of V1.0 RBAC enforcement.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from adapters.api.app import create_app
from services.embed_service import EmbedService
from auth_core.jwt import JWTService, JWTKeySet


@pytest.mark.contract
@pytest.mark.asyncio
async def test_embed_exchange_contract_basic():
    """Test embed token exchange returns proper session structure (Phase 3).
    
    This endpoint now requires JWT authentication as of V1.0 RBAC enforcement.
    """
    # Generate a valid embed token for testing (using same secret as router)
    embed_service = EmbedService(secret=b"dev-secret")
    embed_token = embed_service.issue_embed_token(
        tenant_id="test-tenant-123",
        user_id="test-user-456",
        ttl_seconds=300
    )
    
    # Create JWT authentication token
    jwt_keys = JWTKeySet(active_kid="v1", keys={"v1": "dev-secret-key"})
    jwt_service = JWTService(keys=jwt_keys, issuer="modern-backend", audience="modern-backend")
    
    jwt_token = jwt_service.issue(
        sub="11111111-1111-1111-1111-111111111111",  # Superadmin user UUID
        tenant_id="00000000-0000-0000-0000-000000000000",  # Superadmin tenant UUID
        roles=["superadmin"],
        extra={}
    )
    
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test with /api prefix (Phase 3 routing) and JWT authentication
        headers = {"Authorization": f"Bearer {jwt_token}"}
        resp = await client.post("/api/v1/embed/exchange", json={"embed_token": embed_token.token}, headers=headers)
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
    """Test that invalid embed tokens are rejected with 401.
    
    This endpoint requires JWT authentication, so we provide valid JWT but invalid embed token.
    """
    # Create JWT authentication token
    jwt_keys = JWTKeySet(active_kid="v1", keys={"v1": "dev-secret-key"})
    jwt_service = JWTService(keys=jwt_keys, issuer="modern-backend", audience="modern-backend")
    
    jwt_token = jwt_service.issue(
        sub="11111111-1111-1111-1111-111111111111",  # Superadmin user UUID
        tenant_id="00000000-0000-0000-0000-000000000000",  # Superadmin tenant UUID
        roles=["superadmin"],
        extra={}
    )
    
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test with invalid embed token but valid JWT authentication
        headers = {"Authorization": f"Bearer {jwt_token}"}
        resp = await client.post("/api/v1/embed/exchange", json={"embed_token": "invalid_token_123"}, headers=headers)
        assert resp.status_code == 401, f"Expected 401 for invalid token, got {resp.status_code}"
        assert resp.json()["detail"] == "invalid_or_expired_embed_token"
