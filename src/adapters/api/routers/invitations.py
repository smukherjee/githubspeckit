
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, ConfigDict

from services.rate_limiter import RateLimiter
from adapters.persistence.repositories import SQLAlchemyInvitationRepository
from adapters.api.deps import get_invitation_repo, get_audit_service, AuditService
from domain.invitations.models import InvitationStatus

router = APIRouter(prefix="/v1/invitations", tags=["invitations"])

_limiter = RateLimiter()


class InvitationAcceptResponse(BaseModel):
    invitation_id: str
    status: str
    model_config = ConfigDict()


@router.post("/{invitation_id}/accept", response_model=InvitationAcceptResponse)
async def accept_invitation(
    invitation_id: str,
    request: Request,
    invitation_repo: SQLAlchemyInvitationRepository = Depends(get_invitation_repo),
    audit_service: AuditService = Depends(get_audit_service)
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
    
    # Accept invitation - extract actor from request state (set by ActorTrackingMiddleware)
    actor_user_id = getattr(request.state, "user_id", None) or "system"
    inv.status = InvitationStatus.accepted
    inv.accepted_at = datetime.now(timezone.utc)
    inv.updated_by = actor_user_id
    inv.updated_at = datetime.now(timezone.utc)
    await invitation_repo.upsert(inv)
    
    # Audit logging: Invitation acceptance
    await audit_service.log(
        action_type="invitation.accept",
        tenant_id=inv.tenant_id,
        metadata={
            "invitation_id": inv.invitation_id,
            "email": inv.email,
            "accepted_by": actor_user_id,
            "tenant_id": inv.tenant_id
        }
    )
    
    return InvitationAcceptResponse(invitation_id=inv.invitation_id, status=inv.status.value)
