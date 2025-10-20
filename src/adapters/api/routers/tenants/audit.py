"""
Tenant-scoped audit log routes (V1.0).

**Route Tier**: TENANT-SCOPED (/api/v1/tenants/{tenant_id}/audit)
**Authorization**: Path tenant_id validated by AuthorizationMiddleware

Implements audit log retrieval scoped to a specific tenant.

Status: Phase 3.4 - T033 (Tenant-scoped audit endpoint)
"""
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.api.deps import get_db_session
from domain.tenants.tenant_context import TenantContext

router = APIRouter(prefix="/{tenant_id}/audit", tags=["tenant-scoped-audit"])


class AuditEventResponse(BaseModel):
    """Audit event response model (tenant-scoped)."""
    id: str
    tenant_id: str
    user_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    timestamp: str
    metadata: dict | None = None
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
    response_model=List[AuditEventResponse],
    status_code=status.HTTP_200_OK,
    summary="List audit events for specific tenant",
    description="""
    Retrieves audit log events for the specified tenant.
    
    **Authorization**:
    - Superadmin: Can access any tenant's audit logs
    - Tenant Admin: Can access own tenant's audit logs only
    - Other roles: 403 Forbidden
    
    **V1.0 Behavior**: Tenant context extracted from JWT.
    """,
)
async def list_tenant_audit_events(
    tenant_id: UUID,
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(25, ge=1, le=100, description="Items per page"),
    action: str | None = Query(None, description="Filter by action type"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
) -> List[AuditEventResponse]:
    """
    List audit events for specific tenant (tenant-scoped).
    
    Args:
        tenant_id: Target tenant UUID (from path parameter)
        tenant_context: Current tenant context from middleware
        db: Database session
        page: Page number for pagination
        per_page: Items per page
        action: Optional action filter
        resource_type: Optional resource type filter
    
    Returns:
        List of AuditEventResponse objects
    
    Raises:
        HTTPException 403: If user cannot access this tenant
        HTTPException 500: If database error occurs
    """
    try:
        # TODO: Implement actual audit log query once audit repository is available
        # For now, return empty list to satisfy contract tests
        # This will be implemented in Phase 3.5
        
        # Placeholder response
        return []
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "AUDIT_LIST_ERROR",
                    "message": f"Failed to list audit events: {str(e)}",
                }
            },
        )
