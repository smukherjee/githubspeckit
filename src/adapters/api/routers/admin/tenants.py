"""
Admin tenants management routes (V1.0).

**Route Tier**: ADMIN (/api/v1/admin/tenants)
**Authorization**: Superadmin only

Implements tenant management operations for platform administrators.

Status: Phase 3.4 - T034 (Admin tenants endpoint)
"""
from typing import Annotated, List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.api.deps import get_db_session
from adapters.persistence.repositories import SQLAlchemyTenantRepository
from domain.tenants.tenant_context import TenantContext
from domain.tenants.models import TenantStatus, Tenant

router = APIRouter(prefix="/tenants", tags=["admin"])


class TenantCreateRequest(BaseModel):
    """Request model for creating a tenant (admin)."""
    name: str = Field(..., min_length=1, max_length=255, description="Tenant display name")
    slug: str | None = Field(None, pattern=r"^[a-z0-9-]+$", description="URL-safe slug (auto-generated if omitted)")
    owner_email: EmailStr | None = Field(None, description="Owner email (optional)")
    
    model_config = ConfigDict()


class TenantResponse(BaseModel):
    """Tenant response model (admin)."""
    tenant_id: str
    name: str
    slug: str
    owner_email: EmailStr | None = None
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
        tenants = await repo.list(include_deleted=False)
        
        # Convert to response models
        response_tenants = [
            TenantResponse(
                tenant_id=str(tenant.tenant_id),
                name=tenant.name,
                slug=tenant.name.lower().replace(" ", "-"),  # Auto-generate slug from name
                owner_email=None,  # Not stored in domain model yet
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


@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tenant (superadmin only)",
    description="""
    Creates a new tenant in the platform.
    
    **Authorization**:
    - Superadmin: Full access
    - All other roles: 403 Forbidden
    
    **V1.0 API**: Admin-level tenant creation under /admin namespace.
    """,
)
async def create_tenant(
    request_data: TenantCreateRequest,
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> TenantResponse:
    """
    Create a new tenant (superadmin only).
    
    Args:
        request_data: Tenant creation request
        tenant_context: Current tenant context from middleware
        db: Database session
    
    Returns:
        TenantResponse with created tenant details
    
    Raises:
        HTTPException 403: If user is not superadmin
        HTTPException 409: If tenant slug already exists
        HTTPException 500: If database error occurs
    """
    try:
        # Check if user is superadmin
        if not tenant_context.is_superadmin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "SUPERADMIN_REQUIRED",
                        "message": "Only superadmin can create tenants",
                    }
                },
            )
        
        repo = SQLAlchemyTenantRepository(db)
        
        # Generate slug if not provided
        slug = request_data.slug
        if not slug:
            # Simple slug generation from name
            slug = request_data.name.lower().replace(" ", "-").replace("_", "-")
            slug = "".join(c for c in slug if c.isalnum() or c == "-")
        
        # Check if slug/name already exists
        existing = await repo.get_by_name(request_data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "TENANT_EXISTS",
                        "message": f"Tenant with name '{request_data.name}' already exists",
                    }
                },
            )
        
        # Create tenant domain entity
        tenant = Tenant(
            tenant_id=str(uuid4()),
            name=request_data.name,
            status=TenantStatus.active,
        )
        
        # Save to repository
        created_tenant = await repo.upsert(tenant)
        await db.commit()
        
        return TenantResponse(
            tenant_id=str(created_tenant.tenant_id),
            name=created_tenant.name,
            slug=slug,  # Return the generated slug
            owner_email=request_data.owner_email,
            status=created_tenant.status.value,
            created_at=created_tenant.created_at.isoformat() if created_tenant.created_at else None,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "TENANT_CREATE_ERROR",
                    "message": f"Failed to create tenant: {str(e)}",
                }
            },
        )
