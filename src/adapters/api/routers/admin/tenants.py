"""
Admin tenants management routes (V1.0).

**Route Tier**: ADMIN (/api/v1/admin/tenants)
**Authorization**: Superadmin only

Implements tenant management operations for platform administrators.

Status: Phase 3.4 - T034 (Admin tenants endpoint)
"""
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.api.deps import get_db_session
from adapters.persistence.repositories import SQLAlchemyTenantRepository
from domain.tenants.tenant_context import TenantContext
from domain.tenants.models import TenantStatus

router = APIRouter(prefix="/tenants", tags=["admin-tenants"])


class TenantResponse(BaseModel):
    """Tenant response model (admin)."""
    tenant_id: str
    name: str
    slug: str
    owner_email: EmailStr
    status: str
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
    response_model=List[TenantResponse],
    status_code=status.HTTP_200_OK,
    summary="List all tenants (superadmin only)",
    description="""
    Retrieves all tenants in the platform.
    
    **Authorization**:
    - Superadmin: Full access
    - All other roles: 403 Forbidden
    
    **V1.0 API**: Admin-level tenant listing under /admin namespace.
    """,
)
async def list_all_tenants(
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(25, ge=1, le=100, description="Items per page"),
) -> List[TenantResponse]:
    """
    List all tenants (superadmin only).
    
    Args:
        tenant_context: Current tenant context from middleware
        db: Database session
        page: Page number for pagination
        per_page: Items per page
    
    Returns:
        List of TenantResponse objects
    
    Raises:
        HTTPException 403: If user is not superadmin
        HTTPException 500: If database error occurs
    
    Notes:
        - Authorization middleware should enforce superadmin role
        - This endpoint is not tenant-scoped (returns all tenants)
    """
    try:
        # Check if user is superadmin
        if not tenant_context.is_superadmin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "SUPERADMIN_REQUIRED",
                        "message": "Only superadmin can list all tenants",
                    }
                },
            )
        
        repo = SQLAlchemyTenantRepository(db)
        
        # Query all tenants
        # TODO: Implement list_all() method in repository
        # For now, return empty list as placeholder
        tenants = []
        
        # Convert to response models
        response_tenants = [
            TenantResponse(
                tenant_id=str(tenant.tenant_id),
                name=tenant.name,
                slug=tenant.slug,
                owner_email=tenant.owner_email,
                status=tenant.status.value if hasattr(tenant, 'status') else 'active',
                created_at=tenant.created_at.isoformat() if tenant.created_at else None,
            )
            for tenant in tenants
        ]
        
        # Apply pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        return response_tenants[start_idx:end_idx]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "TENANT_LIST_ERROR",
                    "message": f"Failed to list tenants: {str(e)}",
                }
            },
        )
