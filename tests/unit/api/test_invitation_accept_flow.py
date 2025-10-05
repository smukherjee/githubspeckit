"""TEST-API-11 Invitation accept endpoint flow (basic contract).
Uses existing invitation service create side manually (simulate) then accept via API route.

NOTE: This test needs to be updated for authentication requirements.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from adapters.api.app import create_app
from adapters.api.deps import get_session_maker
from adapters.persistence.repositories import SQLAlchemyInvitationRepository
from services.invitations_service import InvitationService
from uuid import uuid4


@pytest.mark.skip(reason="Needs authentication - invitation flow to be tested in integration tests")
@pytest.mark.asyncio
async def test_invitation_accept_flow():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # create tenant
        tr = await client.post("/v1/tenants", json={"name": "InviteCo"})
        tenant_id = tr.json()["tenant_id"]
        
        # Create invitation directly using database-backed repository
        session_maker = get_session_maker()
        async with session_maker() as session:
            repo = SQLAlchemyInvitationRepository(session)
            svc = InvitationService(repo=repo)  # type: ignore[arg-type]  # TODO: SQLAlchemyInvitationRepository should inherit from InvitationRepository
            inv = await svc.create_invitation(tenant_id=tenant_id, email="newuser@example.com", actor="system")
            await session.commit()
        
        # Accept via API should 200
        ar = await client.post(f"/v1/invitations/{inv.invitation_id}/accept")
        assert ar.status_code == 200
        data = ar.json()
        assert data["status"] == "accepted"
        assert data["invitation_id"] == inv.invitation_id
