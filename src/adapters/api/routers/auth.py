from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime, timezone, timedelta

from auth_core.hashers import default_hasher
from domain.users.models import UserStatus
from adapters.api.deps import get_user_repo, get_auth_service, get_jwt_service

router = APIRouter(prefix="/v1/auth", tags=["auth"])

_UserRepoDep = get_user_repo
_AuthServiceDep = get_auth_service
_JWTDep = get_jwt_service


class LoginRequest(BaseModel):
    user_id: str
    password: str
    mfa_code: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    model_config = ConfigDict()


class RevokeRequest(BaseModel):
    user_id: str


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, user_repo=Depends(_UserRepoDep), auth_service=Depends(_AuthServiceDep), jwt_service=Depends(_JWTDep)):
    user = user_repo.get(payload.user_id)
    if not user or not user.password_hash or user.status != UserStatus.active:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    try:
        result = await auth_service.login_password(user_id=user.user_id, stored_hash=user.password_hash, password=payload.password, mfa_code=payload.mfa_code)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    token = jwt_service.issue(sub=user.user_id, tenant_id=user.tenant_id, roles=user.roles)
    # hash upgrade path
    if result.get("needs_rehash"):
        user.password_hash = default_hasher.hash(payload.password)
    user_repo.upsert(user)
    return LoginResponse(access_token=token, expires_at=datetime.now(timezone.utc) + timedelta(minutes=30))


@router.post("/revoke")
def revoke(payload: RevokeRequest, user_repo=Depends(_UserRepoDep)):
    # placeholder: stateless tokens not tracked yet
    # simulate revoke success
    if not user_repo.get(payload.user_id):
        raise HTTPException(status_code=404, detail="user_not_found")
    return {"revoked": True}
