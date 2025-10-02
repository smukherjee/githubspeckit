from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict

from services.rate_limiter import RateLimiter
from adapters.api.deps import get_invitation_service

router = APIRouter(prefix="/v1/invitations", tags=["invitations"])

_InvitationDep = get_invitation_service
_limiter = RateLimiter()


class InvitationAcceptResponse(BaseModel):
    invitation_id: str
    status: str
    model_config = ConfigDict()


@router.post("/{invitation_id}/accept", response_model=InvitationAcceptResponse)
def accept(invitation_id: str, invitation_service=Depends(_InvitationDep)):
    # simple rate limit: key per invitation
    if not _limiter.allow(f"invite:{invitation_id}"):
        raise HTTPException(status_code=429, detail="rate_limited")
    try:
        inv = invitation_service.accept(invitation_id=invitation_id, actor="system")
    except KeyError:
        raise HTTPException(status_code=404, detail="invitation_not_found")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    return InvitationAcceptResponse(invitation_id=inv.invitation_id, status=inv.status.value)
