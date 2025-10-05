from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import List, Optional
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
import re

from domain.users.models import User, UserStatus
from adapters.api.deps import get_db_session
from adapters.api.auth_deps import CurrentUser
from adapters.persistence.repositories import SQLAlchemyUserRepository, SQLAlchemyTenantRepository
from auth_core.hashers import default_hasher


def validate_password_strength(password: str) -> None:
    """Validate password meets strength requirements.
    
    Requirements:
    - At least 8 characters
    - Contains uppercase letter
    - Contains lowercase letter
    - Contains digit
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")

router = APIRouter(prefix="/v1/users", tags=["users"])


class UserCreateRequest(BaseModel):
    tenant_id: str
    email: EmailStr
    roles: List[str] = []
    password: Optional[str] = None
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            validate_password_strength(v)
        return v
    
    @field_validator('roles')
    @classmethod
    def validate_roles(cls, v: List[str]) -> List[str]:
        """Validate that all roles are in the allowed list."""
        VALID_ROLES = {
            "superadmin", "tenant_admin", "admin", "user", 
            "analyst", "developer", "support_readonly"
        }
        invalid_roles = [r for r in v if r not in VALID_ROLES]
        if invalid_roles:
            raise ValueError(f"Invalid roles: {', '.join(invalid_roles)}. Valid roles are: {', '.join(sorted(VALID_ROLES))}")
        return v


class UserResponse(BaseModel):
    user_id: str
    tenant_id: str
    email: EmailStr
    status: UserStatus
    roles: List[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(use_enum_values=True)


class UserListResponse(BaseModel):
    users: List[UserResponse]


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    payload: UserCreateRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session)
) -> UserResponse:
    user_repo = SQLAlchemyUserRepository(session)
    tenant_repo = SQLAlchemyTenantRepository(session)
    
    # Validate tenant exists
    tenant = await tenant_repo.get(payload.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Tenant isolation: non-superadmins can only create users in their own tenant
    if payload.tenant_id != current_user.tenant_id and not current_user.is_superadmin():
        raise HTTPException(status_code=403, detail="Cannot create users in other tenants")
    
    # Check for duplicate email
    existing_user = await user_repo.get_by_email(payload.email)
    if existing_user:
        raise HTTPException(status_code=409, detail="User with this email already exists")
    
    # Create user
    user = User(
        user_id=str(uuid4()),
        tenant_id=payload.tenant_id,
        email=payload.email,
        roles=payload.roles,
        status=UserStatus.active if payload.password else UserStatus.invited,
        password_hash=default_hasher.hash(payload.password) if payload.password else None,
        created_by=current_user.user_id,
        updated_by=current_user.user_id,
    )
    await user_repo.upsert(user)
    await session.commit()
    
    return UserResponse(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        email=user.email,
        status=user.status,
        roles=user.roles,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("", response_model=UserListResponse)
async def list_users(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    tenant_id: Optional[str] = None
) -> UserListResponse:
    """List users. Defaults to current user's tenant unless tenant_id specified (superadmin only)."""
    # Use current user's tenant if not specified
    effective_tenant_id = tenant_id or current_user.tenant_id
    
    # Only superadmins can query other tenants
    if tenant_id and tenant_id != current_user.tenant_id and not current_user.is_superadmin():
        raise HTTPException(status_code=403, detail="Cannot access other tenant's users")
    
    user_repo = SQLAlchemyUserRepository(session)
    users = await user_repo.list_by_tenant(effective_tenant_id)
    return UserListResponse(users=[
        UserResponse(
            user_id=u.user_id,
            tenant_id=u.tenant_id,
            email=u.email,
            status=u.status,
            roles=u.roles,
            created_at=u.created_at,
            updated_at=u.updated_at
        ) for u in users
    ])


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session)
) -> UserResponse:
    """Get a user by ID with tenant isolation."""
    user_repo = SQLAlchemyUserRepository(session)
    u = await user_repo.get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="user_not_found")
    
    # Tenant isolation: non-superadmins can only access users from their own tenant
    if u.tenant_id != current_user.tenant_id and not current_user.is_superadmin():
        raise HTTPException(status_code=404, detail="user_not_found")
    
    return UserResponse(
        user_id=u.user_id,
        tenant_id=u.tenant_id,
        email=u.email,
        status=u.status,
        roles=u.roles,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


@router.delete("/{user_id}", status_code=204)
async def disable_user(
    user_id: str,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session)
) -> None:
    """Disable a user (soft delete) - Phase 3 database-backed."""
    user_repo = SQLAlchemyUserRepository(session)
    u = await user_repo.get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="user_not_found")
    
    # Tenant isolation: non-superadmins can only disable users from their own tenant
    if u.tenant_id != current_user.tenant_id and not current_user.is_superadmin():
        raise HTTPException(status_code=403, detail="Cannot disable users from other tenants")
    
    # Soft delete: change status to disabled
    u.status = UserStatus.disabled
    u.updated_by = current_user.user_id
    u.updated_at = datetime.now(timezone.utc)
    await user_repo.upsert(u)
    await session.commit()
    # 204 returns no content


@router.post("/{user_id}/restore", status_code=200)
async def restore_user(
    user_id: str,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session)
) -> dict[str, object]:
    """Restore a disabled user (Phase 3 database-backed)."""
    user_repo = SQLAlchemyUserRepository(session)
    u = await user_repo.get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="user_not_found")
    
    # Tenant isolation: non-superadmins can only restore users from their own tenant
    if u.tenant_id != current_user.tenant_id and not current_user.is_superadmin():
        raise HTTPException(status_code=403, detail="Cannot restore users from other tenants")
    
    if u.status != UserStatus.disabled:
        raise HTTPException(status_code=400, detail="user_not_disabled")
    
    u.status = UserStatus.active
    u.updated_by = current_user.user_id
    u.updated_at = datetime.now(timezone.utc)
    await user_repo.upsert(u)
    await session.commit()
    
    return {"user_id": u.user_id, "status": u.status.value}
