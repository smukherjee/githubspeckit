from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any

@dataclass
class AuditEvent:
    event_id: str
    tenant_id: Optional[str]  # Some system events may be global
    category: str
    action: str
    actor_user_id: Optional[str]
    target_type: Optional[str]
    target_id: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0.0"  # API version for tracking schema changes

class AuditAppender:
    def append(self, event: AuditEvent) -> None:  # pragma: no cover - interface only
        raise NotImplementedError

class InMemoryAuditAppender(AuditAppender):
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        self._events.append(event)

    def list(self, tenant_id: Optional[str] = None) -> list[AuditEvent]:
        if tenant_id is None:
            return list(self._events)
        return [e for e in self._events if e.tenant_id == tenant_id]
