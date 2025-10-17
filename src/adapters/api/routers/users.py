from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import List, Optional
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
import re

from domain.users.models import User, UserStatus
from adapters.api.deps import get_db_session, get_audit_service, AuditService
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


class UserUpdateRequest(BaseModel):
    """Request body for updating user core fields.
    
    Note: Extended profile fields (full_name, job_title, department, phone, timezone, language)
    are managed via the /users/{user_id}/profile endpoint (feature 003-user-profile-details).
    This endpoint handles core user fields only: email, roles, and status.
    """
    email: Optional[EmailStr] = None
    roles: Optional[List[str]] = None
    is_disabled: Optional[bool] = None
    
    @field_validator('roles')
    @classmethod
    def validate_roles(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate that all roles are in the allowed list."""
        if v is None:
            return v
        VALID_ROLES = {
            "superadmin", "tenant_admin", "admin", "user", 
            "analyst", "developer", "support_readonly"
        }
        invalid_roles = [r for r in v if r not in VALID_ROLES]
        if invalid_roles:
            raise ValueError(f"Invalid roles: {', '.join(invalid_roles)}. Valid roles are: {', '.join(sorted(VALID_ROLES))}")
        return v


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    payload: UserCreateRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    audit_service: AuditService = Depends(get_audit_service)
) -> UserResponse:
    """Create user with RBAC enforcement (FR-019).
    
    Only tenant_admin (within own tenant) or superadmin can create users.
    """
    # RBAC enforcement: Only tenant_admin or superadmin can create users
    if not (current_user.has_role("tenant_admin") or current_user.is_superadmin()):
        raise HTTPException(
            status_code=403,
            detail="Only tenant admins and superadmins can create users"
        )
    
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
    
    # Audit logging: User creation
    await audit_service.log(
        action_type="user.create",
        tenant_id=user.tenant_id,
        metadata={
            "user_id": user.user_id,
            "email": user.email,
            "roles": user.roles,
            "status": user.status.value,
            "created_by": current_user.user_id
        }
    )
    
    return UserResponse(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        email=user.email,
        status=user.status,
        roles=user.roles,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session)
) -> UserResponse:
    """Get current authenticated user's profile (FR-003).
    
    Any authenticated user can access their own profile.
    """
    user_repo = SQLAlchemyUserRepository(session)
    user = await user_repo.get(current_user.user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
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


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    audit_service: AuditService = Depends(get_audit_service)
) -> UserResponse:
    """Update user profile with RBAC enforcement.
    
    Authorization rules (frontend-agnostic, enforced at API layer):
    - Superadmins: Can update ANY user across all tenants (email, roles, status)
    - Tenant admins: Can update ANY user within their own tenant only (email, roles, status)
    - Regular users: Can update ONLY their own profile (email only - no roles/status changes)
    
    Role escalation prevention:
    - Non-superadmins cannot assign 'superadmin' role
    - Users cannot change their own roles or status
    - Non-superadmins cannot modify superadmin users
    
    Note: Extended profile fields (full_name, job_title, department, phone, timezone, language)
    are stored in the user_details table (feature 003-user-profile-details) and should be
    updated via the /users/{user_id}/profile endpoint.
    """
    user_repo = SQLAlchemyUserRepository(session)
    u = await user_repo.get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="user_not_found")
    
    # Determine if this is a self-update
    is_self_update = (user_id == current_user.user_id)
    
    # RBAC enforcement - Three authorization levels
    # 1. Superadmin: Can update any user across all tenants
    if current_user.is_superadmin():
        # Superadmin can update anyone, but cannot change their own roles/status
        if is_self_update and (payload.roles is not None or payload.is_disabled is not None):
            raise HTTPException(
                status_code=403,
                detail="Cannot modify your own roles or account status"
            )
        # Superadmin allowed to proceed
    
    # 2. Tenant admin: Can update any user within their own tenant
    elif current_user.has_role("tenant_admin"):
        if u.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=403,
                detail="Tenant admins can only update users in their own tenant"
            )
        # Prevent modifying superadmin users unless you are superadmin
        if "superadmin" in u.roles:
            raise HTTPException(
                status_code=403,
                detail="Only superadmins can modify superadmin users"
            )
        # Tenant admin cannot change their own roles/status
        if is_self_update and (payload.roles is not None or payload.is_disabled is not None):
            raise HTTPException(
                status_code=403,
                detail="Cannot modify your own roles or account status"
            )
        # Tenant admin allowed to proceed
    
    # 3. Regular user: Can only update their own profile (email only)
    else:
        if not is_self_update:
            raise HTTPException(
                status_code=403,
                detail="Regular users can only update their own profile"
            )
        # Regular users cannot update roles or status
        if payload.roles is not None or payload.is_disabled is not None:
            raise HTTPException(
                status_code=403,
                detail="Cannot modify your own roles or account status"
            )
        # Regular user allowed to proceed with limited updates
    
    # Track changes for audit logging
    changes_before = {
        "email": u.email,
        "roles": u.roles,
        "status": u.status.value
    }
    
    # Apply updates
    if payload.email is not None and payload.email != u.email:
        # Check email uniqueness
        existing = await user_repo.get_by_email(payload.email)
        if existing and existing.user_id != user_id:
            raise HTTPException(status_code=409, detail="Email already in use")
        u.email = payload.email
    
    # Role updates (admin only)
    if payload.roles is not None:
        # Prevent role escalation
        if "superadmin" in payload.roles and not current_user.is_superadmin():
            raise HTTPException(
                status_code=403,
                detail="Only superadmins can assign the superadmin role"
            )
        # Prevent modifying superadmin users unless you are superadmin
        if "superadmin" in u.roles and not current_user.is_superadmin():
            raise HTTPException(
                status_code=403,
                detail="Only superadmins can modify superadmin users"
            )
        u.roles = payload.roles
    
    # Status updates (admin only)
    if payload.is_disabled is not None:
        u.status = UserStatus.disabled if payload.is_disabled else UserStatus.active
    
    # Update metadata
    u.updated_by = current_user.user_id
    u.updated_at = datetime.now(timezone.utc)
    
    await user_repo.upsert(u)
    await session.commit()
    
    # Track changes for audit logging
    changes_after = {
        "email": u.email,
        "roles": u.roles,
        "status": u.status.value
    }
    
    # Audit logging: User update
    await audit_service.log(
        action_type="user.update",
        tenant_id=u.tenant_id,
        metadata={
            "user_id": u.user_id,
            "email": u.email,
            "updated_by": current_user.user_id,
            "is_self_update": is_self_update,
            "changes": {
                "before": changes_before,
                "after": changes_after
            }
        }
    )
    
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
    session: AsyncSession = Depends(get_db_session),
    audit_service: AuditService = Depends(get_audit_service)
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
    
    # Audit logging: User disable
    await audit_service.log(
        action_type="user.disable",
        tenant_id=u.tenant_id,
        metadata={
            "user_id": u.user_id,
            "email": u.email,
            "disabled_by": current_user.user_id,
            "previous_status": "active"
        }
    )
    # 204 returns no content


@router.post("/{user_id}/restore", status_code=200)
async def restore_user(
    user_id: str,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    audit_service: AuditService = Depends(get_audit_service)
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
    
    # Audit logging: User restore
    await audit_service.log(
        action_type="user.restore",
        tenant_id=u.tenant_id,
        metadata={
            "user_id": u.user_id,
            "email": u.email,
            "restored_by": current_user.user_id,
            "previous_status": "disabled"
        }
    )
    
    return {"user_id": u.user_id, "status": u.status.value}


class PasswordResetRequest(BaseModel):
    """Request body for admin-initiated password reset."""
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        validate_password_strength(v)
        return v


@router.post("/{user_id}/reset-password", status_code=200)
async def reset_user_password(
    user_id: str,
    payload: PasswordResetRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    audit_service: AuditService = Depends(get_audit_service)
) -> dict[str, str]:
    """Reset a user's password (admin-initiated).
    
    RBAC enforcement:
    - tenant_admin can reset passwords for users in their own tenant
    - superadmin can reset passwords for any user
    
    This is different from self-service password reset (/auth/password/reset).
    """
    # RBAC enforcement: Only tenant_admin or superadmin can reset passwords
    if not (current_user.has_role("tenant_admin") or current_user.is_superadmin()):
        raise HTTPException(
            status_code=403,
            detail="Only tenant admins and superadmins can reset user passwords"
        )
    
    user_repo = SQLAlchemyUserRepository(session)
    u = await user_repo.get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="user_not_found")
    
    # Tenant isolation: non-superadmins can only reset passwords for users in their own tenant
    if u.tenant_id != current_user.tenant_id and not current_user.is_superadmin():
        raise HTTPException(
            status_code=403, 
            detail="Cannot reset passwords for users in other tenants"
        )
    
    # Prevent resetting superadmin passwords unless you are a superadmin
    if "superadmin" in u.roles and not current_user.is_superadmin():
        raise HTTPException(
            status_code=403,
            detail="Only superadmins can reset superadmin passwords"
        )
    
    # Hash and update password
    u.password_hash = default_hasher.hash(payload.new_password)
    u.updated_by = current_user.user_id
    u.updated_at = datetime.now(timezone.utc)
    
    # If user was in invited status, activate them
    if u.status == UserStatus.invited:
        u.status = UserStatus.active
    
    await user_repo.upsert(u)
    await session.commit()
    
    # Audit logging: Password reset
    await audit_service.log(
        action_type="user.password_reset",
        tenant_id=u.tenant_id,
        metadata={
            "user_id": u.user_id,
            "email": u.email,
            "reset_by": current_user.user_id,
            "status_changed": u.status == UserStatus.active and "invited" or None
        }
    )
    
    return {
        "message": "Password reset successfully",
        "user_id": u.user_id
    }
