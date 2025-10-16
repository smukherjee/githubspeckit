from fastapi import APIRouter, Query, Depends, Response
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict

from adapters.api.deps import get_db_session
from adapters.persistence.repositories import SQLAlchemyAuditAppender

router = APIRouter(prefix="/v1/audit-events", tags=["audit-events"])


class AuditEventResponse(BaseModel):
    id: str  # React-Admin requires 'id' field
    event_id: str
    tenant_id: str | None
    action: str
    category: str
    actor_user_id: str | None
    # Frontend compatibility fields
    actor_id: str | None  # Maps to actor_user_id
    resource_type: str  # Maps to category  
    resource_id: str | None  # Maps to target.id
    target: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: str
    model_config = ConfigDict()


@router.get("", response_model=list[AuditEventResponse])
@router.get("/", response_model=list[AuditEventResponse])
async def list_events(
    response: Response,
    tenant_id: Optional[str] = None,
    action: Optional[str] = None,
    since: Optional[str] = Query(None, description="ISO8601 lower bound (inclusive)"),
    until: Optional[str] = Query(None, description="ISO8601 upper bound (exclusive)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session)
) -> list[AuditEventResponse]:
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
    
    # Convert to response format for React-Admin
    audit_responses = []
    for e in events:
        audit_response = AuditEventResponse(
            id=e.event_id,  # Use event_id as id for React-Admin
            event_id=e.event_id,
            tenant_id=e.tenant_id,
            action=e.action,
            category=e.category,
            actor_user_id=e.actor_user_id,
            # Frontend compatibility fields
            actor_id=e.actor_user_id,  # Map to actor_user_id
            resource_type=e.category,   # Map category to resource_type
            resource_id=e.target_id,    # Map target_id to resource_id
            target={
                "type": e.target_type,
                "id": e.target_id,
                "tenant_id": e.tenant_id,
            },
            metadata=e.metadata,
            timestamp=e.created_at.isoformat(),
        )
        audit_responses.append(audit_response)
    
    # Add Content-Range header for React-Admin pagination
    total = len(audit_responses)
    response.headers["Content-Range"] = f"audit-events {offset}-{offset + total - 1 if total > 0 else offset}/{offset + total}"
    
    return audit_responses

__all__ = ["router"]
