import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from adapters.api.app import create_app
from services.invitations_service import InvitationService
from domain.invitations.models import InvitationRepository


@pytest.mark.skip(reason="Invitation endpoints require authentication - covered by integration tests")
@pytest.mark.contract
@pytest.mark.asyncio
async def test_invitation_accept_contract_flow():
    """Test invitation accept flow (Phase 3: database-backed).
    
    Note: This test uses the app's configured database and creates an invitation
    directly via the repository, then tests the accept endpoint.
    """
    from uuid import uuid4
    from datetime import datetime, timezone, timedelta
    from adapters.persistence.db_config import DatabaseConfig
    from adapters.persistence.repositories import SQLAlchemyInvitationRepository
    from domain.invitations.models import Invitation
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    
    app = create_app()
    transport = ASGITransport(app=app)
    
    # Use the app's configured database
    db_config = DatabaseConfig.from_env()
    engine = db_config.create_engine()
    async_session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create tenant first (with /api prefix)
        tr = await client.post("/api/v1/tenants", json={"name": "InvitationFlow"})
        assert tr.status_code == 201, f"Tenant creation failed: {tr.text}"
        tenant_id = tr.json()["tenant_id"]
        
        # Create invitation directly in database
        invitation_id = str(uuid4())
        async with async_session_maker() as session:
            repo = SQLAlchemyInvitationRepository(session)
            inv = Invitation(
                invitation_id=invitation_id,
                tenant_id=tenant_id,
                email="invflow@example.com",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                created_by="system",
                updated_by="system",
            )
            await repo.upsert(inv)
            await session.commit()

        # Accept invitation via API
        ar = await client.post(f"/api/v1/invitations/{invitation_id}/accept")
        assert ar.status_code == 200, f"Accept failed: {ar.text}"
        data = ar.json()
        assert data["invitation_id"] == invitation_id
        assert data["status"] == "accepted"
    
    # Cleanup
    await engine.dispose()
