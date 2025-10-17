from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from services.embed_service import EmbedService
from pydantic import BaseModel, ConfigDict
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.api.deps import get_db_session

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
async def exchange(
    payload: EmbedExchangeRequest,
    session: AsyncSession = Depends(get_db_session)
) -> EmbedSession:
    """Exchange embed token for session (FR-054: full cryptographic verification)."""
    # Validate origin if provided (development mode permissive for localhost)
    if payload.origin and not service.validate_origin(payload.origin):
        raise HTTPException(status_code=400, detail="origin_not_allowed")
    
    # FR-054: Cryptographically verify embed token (HMAC-SHA256 signature)
    if not payload.embed_token:
        raise HTTPException(status_code=400, detail="invalid_embed_token")
    
    if not service.verify_embed_token(payload.embed_token):
        raise HTTPException(status_code=401, detail="invalid_or_expired_embed_token")
    
    # Extract tenant_id and user_id from verified token
    try:
        import base64
        parts = payload.embed_token.split(".", 1)
        if len(parts) != 2:
            raise HTTPException(status_code=401, detail="malformed_embed_token")
        
        payload_b64 = parts[0]
        pad = -len(payload_b64) % 4
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + ("=" * pad))
        tenant_id, user_id, _ = payload_bytes.decode("utf-8").split("|")
    except Exception:
        raise HTTPException(status_code=401, detail="invalid_embed_token_format")
    
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=5)
    
    return EmbedSession(
        session_id=str(uuid4()),
        tenant_id=tenant_id,
        user_id=user_id,
        roles=[],  # Roles can be expanded based on tenant/user lookup
        issued_at=now,
        expires_at=expires,
    )
