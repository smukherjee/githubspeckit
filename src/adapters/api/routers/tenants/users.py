"""
Tenant-scoped user management routes (FR-004 tenant security refactor).

**Route Tier**: TENANT-SCOPED (/api/v1/tenants/{tenant_id}/users)
**Authorization**: Path tenant_id validated by AuthorizationMiddleware

Implements user management operations scoped to a specific tenant.
The tenant_id in the path is the source of truth, not the JWT tenant_id.
This enables superadmin cross-tenant operations.

**Authorization Flow**:
1. TenantContextMiddleware extracts JWT tenant_id → request.state.tenant_context
2. AuthorizationMiddleware evaluates: Can user access path tenant_id?
3. If DENY: 403 with X-Tenant-Isolation-Policy header
4. If ALLOW: Request proceeds to endpoint

**Use Cases**:
- Superadmin: Switch tenant via session → access any tenant's users
- Tenant admin: Can only access own tenant (tenant_id == JWT tenant_id)

Status: Phase 3.4 - Endpoint Implementation (T038)
"""
from __future__ import annotations

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.api.deps import get_db_session
from adapters.persistence.repositories import SQLAlchemyUserRepository
from domain.tenants.tenant_context import TenantContext
from domain.users.models import UserStatus

router = APIRouter(prefix="/{tenant_id}/users", tags=["tenant-scoped-users"])


class UserResponse(BaseModel):
    """User response model (tenant-scoped)."""
    user_id: str
    tenant_id: str
    email: EmailStr
    status: UserStatus
    roles: List[str]
    created_at: str | None = None
    updated_at: str | None = None
    model_config = ConfigDict(use_enum_values=True)


class UserListResponse(BaseModel):
    """Paginated user list response."""
    users: List[UserResponse]
    pagination: dict


def get_tenant_context(request: Request) -> TenantContext:
    """
    Extract tenant context from request state.
    
    Injected by TenantContextMiddleware in Phase 3.3.
    
    Args:
        request: FastAPI request object
    
    Returns:
        TenantContext from request.state
    
    Raises:
        HTTPException: 500 if tenant context not found (middleware not wired)
    """
    if not hasattr(request.state, "tenant_context"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "TENANT_CONTEXT_MISSING",
                    "message": "Tenant context not initialized (middleware not wired)",
                }
            },
        )
    return request.state.tenant_context


@router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List users in specific tenant",
    description="""
    Retrieves all users belonging to the specified tenant.
    
    **Authorization**:
    - Superadmin: Can access any tenant
    - Tenant Admin: Can access own tenant only (tenant_id == JWT tenant_id)
    - Other roles: 403 Forbidden
    
    **Migration Note**: Replaces deprecated `GET /users?tenant_id={id}`
    
    **Tenant Context**: The tenant_id in the path is validated by AuthorizationMiddleware
    against the JWT tenant_id. Cross-tenant access is denied unless user is superadmin.
    
    **Pagination**: Uses page/per_page query parameters
    """,
)
async def list_tenant_users(
    tenant_id: UUID,
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(25, ge=1, le=100, description="Items per page"),
) -> UserListResponse:
    """
    List users in specific tenant (tenant-scoped).
    
    Args:
        tenant_id: Target tenant UUID (from path parameter)
        tenant_context: Current tenant context from middleware
        db: Database session
        page: Page number for pagination
        per_page: Items per page
    
    Returns:
        UserListResponse with users and pagination metadata
    
    Raises:
        HTTPException 403: If user cannot access this tenant (handled by middleware)
        HTTPException 500: If database error occurs
    
    Notes:
        - Authorization already handled by AuthorizationMiddleware
        - This endpoint trusts the path tenant_id (middleware validated it)
        - Superadmin access logged by middleware (audit trail)
    """
    # Authorization already enforced by AuthorizationMiddleware
    # If we reach here, user has permission to access this tenant
    
    # Use path tenant_id (not JWT tenant_id) for query
    # This enables superadmin cross-tenant access
    user_repo = SQLAlchemyUserRepository(db)
    
    try:
        # Calculate pagination offset
        offset = (page - 1) * per_page
        
        # Query users by path tenant_id
        from sqlalchemy import select, func
        from adapters.persistence.models import UserModel, UserRoleModel
        
        # Get total count
        count_query = select(func.count(UserModel.user_id)).where(
            UserModel.tenant_id == tenant_id
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get paginated users
        query = select(UserModel).where(
            UserModel.tenant_id == tenant_id
        ).offset(offset).limit(per_page).order_by(UserModel.created_at.desc())
        
        result = await db.execute(query)
        user_models = result.scalars().all()
        
        # For each user, fetch their roles from user_roles table
        users = []
        for user in user_models:
            # Fetch roles
            roles_query = select(UserRoleModel.role_id).where(
                UserRoleModel.user_id == user.user_id
            )
            roles_result = await db.execute(roles_query)
            roles = [row[0] for row in roles_result.fetchall()]
            
            users.append(
                UserResponse(
                    user_id=str(user.user_id),
                    tenant_id=str(user.tenant_id),
                    email=user.email,
                    status=UserStatus(user.status.value) if hasattr(user.status, 'value') else UserStatus(user.status),
                    roles=roles,
                    created_at=user.created_at.isoformat() if user.created_at else None,
                    updated_at=user.updated_at.isoformat() if user.updated_at else None,
                )
            )
        
        # Build pagination metadata
        pagination = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        }
        
        return UserListResponse(users=users, pagination=pagination)
        
    except Exception as e:
        # Log error and return 500
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": f"Failed to query users: {str(e)}",
                },
            },
        )
