from fastapi import APIRouter, Query, Depends
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.api.deps import get_db_session
from adapters.persistence.repositories import SQLAlchemyAuditAppender

router = APIRouter(prefix="/v1/audit", tags=["audit"])


@router.get("/events")
async def list_events(
    tenant_id: Optional[str] = None,
    action: Optional[str] = None,
    since: Optional[str] = Query(None, description="ISO8601 lower bound (inclusive)"),
    until: Optional[str] = Query(None, description="ISO8601 upper bound (exclusive)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """List audit events with filtering (FR-027).
    
    Supports filtering by tenant_id, action, since, until timestamps.
    Filters are applied in SQL for efficiency.
    """
    appender = SQLAlchemyAuditAppender(session)
    
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
        tenant_id=tenant_id,
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
