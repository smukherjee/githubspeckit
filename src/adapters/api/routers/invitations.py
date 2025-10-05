from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict

from services.rate_limiter import RateLimiter
from adapters.persistence.repositories import SQLAlchemyInvitationRepository
from adapters.api.deps import get_invitation_repo
from domain.invitations.models import InvitationStatus

router = APIRouter(prefix="/v1/invitations", tags=["invitations"])

_limiter = RateLimiter()


class InvitationAcceptResponse(BaseModel):
    invitation_id: str
    status: str
    model_config = ConfigDict()


@router.post("/{invitation_id}/accept", response_model=InvitationAcceptResponse)
async def accept(
    invitation_id: str,
    invitation_repo: SQLAlchemyInvitationRepository = Depends(get_invitation_repo)
) -> InvitationAcceptResponse:
    """Accept an invitation (Phase 3: database-backed).
    
    Uses SQLAlchemyInvitationRepository directly for async database operations.
    """
    # simple rate limit: key per invitation
    if not _limiter.allow(f"invite:{invitation_id}"):
        raise HTTPException(status_code=429, detail="rate_limited")
    
    # Get invitation
    inv = await invitation_repo.get(invitation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="invitation_not_found")
    
    # Check if already accepted (idempotent)
    if inv.status == InvitationStatus.accepted:
        return InvitationAcceptResponse(invitation_id=inv.invitation_id, status=inv.status.value)
    
    # Check if pending
    if inv.status != InvitationStatus.pending:
        raise HTTPException(status_code=400, detail="invitation_not_active")
    
    # Check if expired
    if inv.is_expired():
        inv.status = InvitationStatus.expired
        inv.updated_at = datetime.now(timezone.utc)
        await invitation_repo.upsert(inv)
        raise HTTPException(status_code=400, detail="invitation_expired")
    
    # Accept invitation
    inv.status = InvitationStatus.accepted
    inv.accepted_at = datetime.now(timezone.utc)
    inv.updated_by = "system"  # TODO: Extract from auth context
    inv.updated_at = datetime.now(timezone.utc)
    await invitation_repo.upsert(inv)
    
    return InvitationAcceptResponse(invitation_id=inv.invitation_id, status=inv.status.value)
