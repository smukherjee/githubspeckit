"""
Admin users management routes (V1.0).

**Route Tier**: ADMIN (/api/v1/admin/users)
**Authorization**: Superadmin only

Implements user management operations across all tenants for platform administrators.

Status: Phase 3.4 - T035 (Admin users endpoint)
"""
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.api.deps import get_db_session
from adapters.persistence.repositories import SQLAlchemyUserRepository
from domain.tenants.tenant_context import TenantContext
from domain.users.models import UserStatus

router = APIRouter(prefix="/users", tags=["admin"])


class UserResponse(BaseModel):
    """User response model (admin - cross-tenant)."""
    user_id: str
    tenant_id: str
    email: EmailStr
    status: str
    roles: List[str]
    created_at: str | None = None
    model_config = ConfigDict()


def get_tenant_context(request: Request) -> TenantContext:
    """Extract tenant context from request state (injected by middleware)."""
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
    response_model=List[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="List all users across tenants (superadmin only)",
    description="""
    Retrieves all users across all tenants in the platform.
    
    **Authorization**:
    - Superadmin: Full access to all users
    - All other roles: 403 Forbidden
    
    **V1.0 API**: Admin-level user listing under /admin namespace.
    """,
)
async def list_all_users(
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(25, ge=1, le=100, description="Items per page"),
    tenant_id: UUID | None = Query(None, description="Optional: filter by tenant"),
) -> List[UserResponse]:
    """
    List all users across tenants (superadmin only).
    
    Args:
        tenant_context: Current tenant context from middleware
        db: Database session
        page: Page number for pagination
        per_page: Items per page
        tenant_id: Optional tenant filter
    
    Returns:
        List of UserResponse objects
    
    Raises:
        HTTPException 403: If user is not superadmin
        HTTPException 500: If database error occurs
    
    Notes:
        - Authorization middleware should enforce superadmin role
        - This endpoint is not tenant-scoped (returns users from all tenants)
        - Optional tenant_id filter for narrowing results
    """
    try:
        # Check if user is superadmin
        if not tenant_context.is_superadmin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "SUPERADMIN_REQUIRED",
                        "message": "Only superadmin can list all users",
                    }
                },
            )
        
        repo = SQLAlchemyUserRepository(db)
        
        # Query users (optionally filtered by tenant)
        if tenant_id:
            users = await repo.list_by_tenant(tenant_id=str(tenant_id))
        else:
            # TODO: Implement list_all() method in repository
            # For now, return empty list as placeholder
            users = []
        
        # Convert to response models
        response_users = [
            UserResponse(
                user_id=str(user.user_id),
                tenant_id=str(user.tenant_id),
                email=user.email,
                status=user.status.value if hasattr(user, 'status') else 'active',
                roles=user.roles if user.roles else [],
                created_at=user.created_at.isoformat() if user.created_at else None,
            )
            for user in users
        ]
        
        # Apply pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        return response_users[start_idx:end_idx]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "USER_LIST_ERROR",
                    "message": f"Failed to list users: {str(e)}",
                }
            },
        )
