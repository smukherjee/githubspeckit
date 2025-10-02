from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List, Optional
from uuid import uuid4
from datetime import datetime, timezone

from domain.users.models import User, UserStatus
from adapters.api.deps import get_user_repo, get_user_lifecycle
from auth_core.hashers import default_hasher

router = APIRouter(prefix="/v1/users", tags=["users"])

_UserRepoDep = get_user_repo  # alias for clarity
_LifecycleDep = get_user_lifecycle


class UserCreateRequest(BaseModel):
    tenant_id: str
    email: EmailStr
    roles: List[str] = []
    password: Optional[str] = None


class UserResponse(BaseModel):
    user_id: str
    tenant_id: str
    email: EmailStr
    status: UserStatus
    roles: List[str]
    model_config = ConfigDict(use_enum_values=True)


class UserListResponse(BaseModel):
    users: List[UserResponse]


@router.post("", response_model=UserResponse, status_code=201)
def create_user(payload: UserCreateRequest, user_repo=Depends(_UserRepoDep)):
    # simplistic create: no duplicate email check
    user = User(
        user_id=str(uuid4()),
        tenant_id=payload.tenant_id,
        email=payload.email,
        roles=payload.roles,
        status=UserStatus.active if payload.password else UserStatus.invited,
        password_hash=default_hasher.hash(payload.password) if payload.password else None,
        created_by="system",
        updated_by="system",
    )
    user_repo.upsert(user)
    return UserResponse(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        email=user.email,
        status=user.status,
        roles=user.roles,
    )


@router.get("", response_model=UserListResponse)
def list_users(tenant_id: str, user_repo=Depends(_UserRepoDep)):  # tenant_id required per multi-tenancy principle
    users = user_repo.list_by_tenant(tenant_id)
    return UserListResponse(users=[UserResponse(user_id=u.user_id, tenant_id=u.tenant_id, email=u.email, status=u.status, roles=u.roles) for u in users])


@router.post("/{user_id}/disable")
def disable_user(user_id: str, lifecycle=Depends(_LifecycleDep)):
    try:
        u = lifecycle.disable(user_id=user_id, actor="system")
    except KeyError:
        raise HTTPException(status_code=404, detail="user_not_found")
    return {"user_id": u.user_id, "status": u.status}


@router.post("/{user_id}/restore")
def restore_user(user_id: str, lifecycle=Depends(_LifecycleDep)):
    try:
        u = lifecycle.restore(user_id=user_id, actor="system")
    except KeyError:
        raise HTTPException(status_code=404, detail="user_not_found")
    except ValueError:
        raise HTTPException(status_code=400, detail="user_not_disabled")
    return {"user_id": u.user_id, "status": u.status}
