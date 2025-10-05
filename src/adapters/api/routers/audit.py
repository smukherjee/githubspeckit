from fastapi import APIRouter, Query
from datetime import datetime, timezone
from typing import Optional

from services.audit_service import AuditService

router = APIRouter(prefix="/v1/audit", tags=["audit"])

_audit = AuditService()  # in-memory for phase 2


@router.get("/events")
async def list_events(
    tenant_id: Optional[str] = None,
    action: Optional[str] = None,
    since: Optional[str] = Query(None, description="ISO8601 lower bound (inclusive)"),
    until: Optional[str] = Query(None, description="ISO8601 upper bound (exclusive)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, int | list[dict[str, object]]]:
    events = _audit.query()
    # filtering
    def parse(ts: str) -> datetime:
        return datetime.fromisoformat(ts)
    out = []
    for e in events:
        if tenant_id and e["target"].get("tenant_id") != tenant_id:
            continue
        if action and e["action"] != action:
            continue
        if since:
            try:
                if parse(e["timestamp"]) < datetime.fromisoformat(since):
                    continue
            except Exception:
                pass
        if until:
            try:
                if parse(e["timestamp"]) >= datetime.fromisoformat(until):
                    continue
            except Exception:
                pass
        out.append(e)
    total = len(out)
    window = out[offset : offset + limit]
    return {"total": total, "count": len(window), "items": window, "offset": offset, "limit": limit}

__all__ = ["router", "_audit"]
