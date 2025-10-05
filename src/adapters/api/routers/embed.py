from fastapi import APIRouter, HTTPException
from typing import Optional
from services.embed_service import EmbedService
from pydantic import BaseModel, ConfigDict
from uuid import uuid4
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/v1/embed", tags=["Embed"])  # Capitalize tag to match spec fragment

# Primitive wiring: create in-memory service instance.
service = EmbedService(secret=b"dev-secret", allowed_origins=None)


class EmbedExchangeRequest(BaseModel):
    embed_token: str
    origin: Optional[str] = None
    user_id: Optional[str] = None


class EmbedSession(BaseModel):
    session_id: str
    tenant_id: str
    user_id: Optional[str] = None
    roles: list[str] = []
    expires_at: datetime
    issued_at: datetime
    model_config = ConfigDict()


@router.post("/exchange", response_model=EmbedSession)
async def exchange(payload: EmbedExchangeRequest) -> EmbedSession:
    # Minimal validation: origin check (development permissive) + token presence.
    if payload.origin and not service.validate_origin(payload.origin):
        raise HTTPException(status_code=400, detail="origin_not_allowed")
    # TODO: verify embed token cryptographically (future). For now accept any non-empty string.
    if not payload.embed_token:
        raise HTTPException(status_code=400, detail="invalid_embed_token")
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=5)
    # Derive tenant_id from token in future; placeholder default.
    return EmbedSession(
        session_id=str(uuid4()),
        tenant_id="default",
        user_id=payload.user_id,
        roles=[],
        issued_at=now,
        expires_at=expires,
    )
