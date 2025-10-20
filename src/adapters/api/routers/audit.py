from fastapi import APIRouter, Query, Depends, Request
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.api.deps import get_db_session
from adapters.persistence.repositories import SQLAlchemyAuditAppender
from domain.tenants.tenant_context import TenantContext

router = APIRouter(prefix="/v1/audit", tags=["audit"])


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
    from fastapi import HTTPException, status
    
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


@router.get("/events")
async def list_events(
    request: Request,
    tenant_context: TenantContext = Depends(get_tenant_context),
    action: Optional[str] = None,
    since: Optional[str] = Query(None, description="ISO8601 lower bound (inclusive)"),
    until: Optional[str] = Query(None, description="ISO8601 upper bound (exclusive)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """List audit events with filtering (FR-027, FR-004 tenant security refactor).
    
    **V1.0 Behavior**: Tenant context extracted from JWT (or session for superadmin).
    Cross-tenant access requires superadmin session switching (POST /admin/context/tenant).
    
    **Authorization**: Middleware enforces tenant isolation
    
    Supports filtering by action, since, until timestamps.
    Filters are applied in SQL for efficiency.
    """
    appender = SQLAlchemyAuditAppender(session)
    
    # Use effective_tenant_id from tenant context (handles superadmin session switching)
    filter_tenant_id = str(tenant_context.effective_tenant_id)
    
    # Parse timestamp strings to datetime objects
    since_dt = None
    until_dt = None
    
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail=f"Invalid 'since' timestamp format: {since}. Expected ISO8601."
            )
    
    if until:
        try:
            until_dt = datetime.fromisoformat(until.replace("Z", "+00:00"))
        except ValueError:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail=f"Invalid 'until' timestamp format: {until}. Expected ISO8601."
            )
    
    # Fetch events from database with all filters applied in SQL (FR-027)
    events = await appender.list(
        tenant_id=filter_tenant_id,
        action=action,
        since=since_dt,
        until=until_dt,
        limit=limit,
        offset=offset
    )
    
    # Convert to dict format for response
    items = []
    for e in events:
        event_dict = {
            "event_id": e.event_id,
            "tenant_id": e.tenant_id,
            "action": e.action,
            "category": e.category,
            "actor_user_id": e.actor_user_id,
            "target": {
                "type": e.target_type,
                "id": e.target_id,
                "tenant_id": e.tenant_id,
            },
            "metadata": e.metadata,
            "timestamp": e.created_at.isoformat(),
        }
        items.append(event_dict)
    
    # Return paginated response
    return {
        "total": len(items),  # Note: This is count of filtered results, not total in DB
        "count": len(items),
        "items": items,
        "offset": offset,
        "limit": limit
    }

__all__ = ["router"]
