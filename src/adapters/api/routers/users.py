from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query, Request, status
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import List, Optional, Annotated
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
import re

from domain.users.models import User, UserStatus
from adapters.api.deps import get_db_session, get_audit_service, AuditService
from adapters.api.auth_deps import CurrentUser
from adapters.persistence.repositories import SQLAlchemyUserRepository, SQLAlchemyTenantRepository
from auth_core.hashers import default_hasher
from services.csv_import_service import CSVImportService
from domain.tenants.tenant_context import TenantContext


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
    
    # Check for duplicate email within tenant (V1.0: per-tenant email uniqueness - FR-116)
    existing_user = await user_repo.get_by_email_and_tenant(payload.email, payload.tenant_id)
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail=f"Email '{payload.email}' is already registered in this tenant"
        )
    
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
    tenant_id: Optional[str] = None,
    include_deleted: bool = False
) -> UserListResponse:
    """List users (FR-087: supports include_deleted parameter). Defaults to current user's tenant unless tenant_id specified (superadmin only)."""
    # Use current user's tenant if not specified
    effective_tenant_id = tenant_id or current_user.tenant_id
    
    # Only superadmins can query other tenants
    if tenant_id and tenant_id != current_user.tenant_id and not current_user.is_superadmin():
        raise HTTPException(status_code=403, detail="Cannot access other tenant's users")
    
    user_repo = SQLAlchemyUserRepository(session)
    users = await user_repo.list_by_tenant(effective_tenant_id, include_deleted=include_deleted)
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
        # Check email uniqueness within tenant (V1.0: per-tenant email uniqueness - FR-116)
        existing = await user_repo.get_by_email_and_tenant(payload.email, u.tenant_id)
        if existing and existing.user_id != user_id:
            raise HTTPException(
                status_code=409,
                detail=f"Email '{payload.email}' is already in use in this tenant"
            )
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


@router.post("/import")
async def import_users_csv(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    audit_service: AuditService = Depends(get_audit_service),
    file: UploadFile = File(..., description="CSV file with user data (email, roles, tenant_id, full_name, job_title)"),
    dry_run: bool = Query(False, description="Preview import without creating users")
):
    """Bulk import users from CSV file (FR-088, T008).
    
    **CSV Format**:
    ```csv
    email,roles,tenant_id,full_name,job_title
    user@example.com,user,tenant-123,John Doe,Engineer
    admin@example.com,"tenant_admin,developer",tenant-123,Jane Smith,Manager
    ```
    
    **Required Fields**: email, roles, tenant_id
    **Optional Fields**: full_name, job_title
    
    **Validation**:
    - Email format (regex)
    - Valid roles (7 allowed: superadmin, tenant_admin, developer, analyst, user, service_account, support_readonly)
    - Tenant isolation (non-superadmin restricted to own tenant)
    - Duplicate email detection
    
    **RBAC**:
    - Superadmin: Can import to any tenant
    - Tenant_admin: Restricted to own tenant
    - Other roles: Forbidden (403)
    
    **Dry Run**: Set `dry_run=true` to preview results without creating users.
    
    **Response**: Import summary with success_count, error_count, errors[], preview[] (if dry_run).
    """
    # RBAC: Only tenant_admin and superadmin can import users
    is_superadmin = "superadmin" in current_user.roles
    is_tenant_admin = "tenant_admin" in current_user.roles
    
    if not (is_superadmin or is_tenant_admin):
        raise HTTPException(
            status_code=403,
            detail="CSV import requires tenant_admin or superadmin role"
        )
    
    # Read CSV file
    try:
        content = await file.read()
        csv_text = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid CSV file: must be UTF-8 encoded"
        )
    
    # Import users via service
    user_repo = SQLAlchemyUserRepository(session)
    service = CSVImportService(user_repo)
    
    result = await service.import_users(
        csv_content=csv_text,
        dry_run=dry_run,
        current_user_tenant_id=current_user.tenant_id,
        is_superadmin=is_superadmin
    )
    
    # Audit logging (only for actual imports, not dry-runs)
    if not dry_run:
        await audit_service.log(
            action_type="user.bulk_import",
            tenant_id=current_user.tenant_id,
            metadata={
                "imported_by": current_user.user_id,
                "success_count": result["success_count"],
                "error_count": result["error_count"],
                "total_rows": result["success_count"] + result["error_count"]
            }
        )
    
    return result


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="""
    Retrieves the authenticated user's profile (SELF-SERVICE route).
    
    **Authorization**: Any authenticated user
    **Tenant Context**: Automatically scoped to user's tenant from JWT
    
    **Implementation Note**: Uses effective_tenant_id from tenant_context
    to handle superadmin session switching. When a superadmin switches tenants,
    this endpoint will return their profile scoped to the session tenant.
    
    **Migration Note**: Part of FR-004 tenant security refactor.
    Tenant ID extracted from JWT (not query parameter).
    """,
)
async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[CurrentUser, Depends()],
    request: Request,
) -> UserResponse:
    """
    Get current user profile (self-service).
    
    Args:
        session: Database session
        current_user: Authenticated user from JWT
        request: FastAPI request (for tenant context)
    
    Returns:
        UserResponse with current user details
    
    Raises:
        HTTPException 404: If user not found (should not happen with valid JWT)
        HTTPException 500: If tenant context missing or database error
    """
    # Extract tenant context from request state (injected by middleware)
    if not hasattr(request.state, "tenant_context"):
        # Fallback: Use JWT tenant_id if middleware not wired yet
        effective_tenant_id = current_user.tenant_id
    else:
        tenant_context: TenantContext = request.state.tenant_context
        # Use effective_tenant_id (handles superadmin session switching)
        effective_tenant_id = tenant_context.effective_tenant_id
    
    # Query user by user_id and effective tenant_id
    user_repo = SQLAlchemyUserRepository(session)
    
    try:
        # Get user from database
        from adapters.persistence.models import UserModel, UserRoleModel
        from sqlalchemy import select
        
        query = select(UserModel).where(
            UserModel.user_id == current_user.user_id,
            UserModel.tenant_id == effective_tenant_id
        )
        result = await session.execute(query)
        user_model = result.scalar_one_or_none()
        
        if not user_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"User '{current_user.user_id}' not found in tenant '{effective_tenant_id}'",
                    },
                    "trace_id": request.headers.get("X-Correlation-ID", "unknown"),
                },
            )
        
        # Fetch user roles
        roles_query = select(UserRoleModel.role_id).where(
            UserRoleModel.user_id == user_model.user_id
        )
        roles_result = await session.execute(roles_query)
        roles = [row[0] for row in roles_result.fetchall()]
        
        # Return user response
        return UserResponse(
            user_id=str(user_model.user_id),
            tenant_id=str(user_model.tenant_id),
            email=user_model.email,
            status=UserStatus(user_model.status.value) if hasattr(user_model.status, 'value') else UserStatus(user_model.status),
            roles=roles,
            created_at=user_model.created_at,
            updated_at=user_model.updated_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": f"Failed to query user: {str(e)}",
                },
                "trace_id": request.headers.get("X-Correlation-ID", "unknown"),
            },
        )

