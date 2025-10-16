from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

from services.rate_limiter import RateLimiter
from adapters.persistence.repositories import SQLAlchemyInvitationRepository
from adapters.api.deps import get_invitation_repo
from domain.invitations.models import InvitationStatus

router = APIRouter(prefix="/v1/invitations", tags=["invitations"])

_limiter = RateLimiter()


class InvitationResponse(BaseModel):
    id: str  # React-Admin requires 'id' field
    invitation_id: str
    status: str
    email: Optional[str] = None
    tenant_id: Optional[str] = None
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    model_config = ConfigDict()


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


@router.get("", response_model=list[InvitationResponse])
async def list_invitations(
    response: Response,
    invitation_repo: SQLAlchemyInvitationRepository = Depends(get_invitation_repo)
) -> list[InvitationResponse]:
    """List invitations (Phase 3: database-backed)."""
    # TODO: Add filtering by tenant_id, status, etc.
    # For now, return empty list as we don't have a list_all method
    invitation_responses = []
    
    # Add Content-Range header for React-Admin pagination
    total = len(invitation_responses)
    response.headers["Content-Range"] = f"invitations 0-{total-1 if total > 0 else 0}/{total}"
    
    return invitation_responses
