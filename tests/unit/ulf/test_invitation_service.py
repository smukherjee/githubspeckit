import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from domain.invitations.models import Invitation, InvitationStatus
from adapters.api.deps import get_session_maker
from adapters.persistence.repositories import SQLAlchemyInvitationRepository
from services.invitations_service import InvitationService


@pytest.mark.asyncio
async def test_invitation_accept_idempotent():
    """Test invitation acceptance is idempotent (can be accepted multiple times)."""
    from domain.tenants.models import Tenant
    from adapters.persistence.repositories import SQLAlchemyTenantRepository
    
    # Generate proper UUIDs
    inv_id = str(uuid4())
    tenant_id = str(uuid4())
    
    session_maker = get_session_maker()
    # Keep one session open for the entire test
    async with session_maker() as session:
        # Create tenant first (foreign key requirement)
        tenant_repo = SQLAlchemyTenantRepository(session)
        tenant = Tenant(
            tenant_id=tenant_id,
            name=f"test_tenant_{uuid4().hex[:8]}",
            created_by="system",
            updated_by="system",
        )
        await tenant_repo.upsert(tenant)
        await session.commit()
        
        # Now create invitation
        repo = SQLAlchemyInvitationRepository(session)
        svc = InvitationService(repo)  # type: ignore[arg-type]
        
        now = datetime.now(timezone.utc)
        inv = Invitation(
            invitation_id=inv_id,
            tenant_id=tenant_id,
            email="a@example.com",
            expires_at=now + timedelta(hours=1),
            status=InvitationStatus.pending,
            created_by="system",
            updated_by="system",
        )
        await repo.upsert(inv)
        await session.commit()
        
        # Test first accept - should succeed
        accepted = await svc.accept(inv_id, actor="system")
        assert accepted.status == InvitationStatus.accepted
        assert accepted.accepted_at is not None
        await session.commit()
        
        # Second accept is idempotent and returns same accepted invitation
        again = await svc.accept(inv_id, actor="system")
        assert again.status == InvitationStatus.accepted
        assert again.invitation_id == inv_id
        await session.commit()


@pytest.mark.asyncio
async def test_accept_nonexistent_raises():
    # Use a valid UUID format
    nonexistent_id = str(uuid4())
    
    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = SQLAlchemyInvitationRepository(session)
        svc = InvitationService(repo)  # type: ignore[arg-type]  # TODO: SQLAlchemyInvitationRepository should inherit from InvitationRepository
        with pytest.raises(KeyError):
            await svc.accept(nonexistent_id, actor="x")
