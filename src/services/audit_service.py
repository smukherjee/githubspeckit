from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from adapters.logging.redaction import redact_dict



@dataclass
class AuditEvent:
    timestamp: str
    actor: str
    action: str
    target: Dict[str, Any]
    metadata: Dict[str, Any]


class InMemoryAuditStore:
    def __init__(self):
        self.events: List[AuditEvent] = []

    def append(self, event: AuditEvent):
        self.events.append(event)

    def list(self) -> List[AuditEvent]:
        return list(self.events)


class AuditService:
    def __init__(self, store: InMemoryAuditStore | None = None, exporter: Optional[object] = None, metrics_adapter=None):
        self.store = store or InMemoryAuditStore()
        # optional exporter with .export(list_of_events)
        self.exporter = exporter
        # optional prometheus-like adapter for emitting redaction_violation metric
        self._metrics = metrics_adapter

    def emit(self, actor: str, action: str, target: Dict[str, Any], metadata: Dict[str, Any] | None = None):
        metadata = metadata or {}
        # redact metadata defensively
        redacted_meta, had_secret = redact_dict(metadata)
        ev = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor=actor,
            action=action,
            target=target,
            metadata=redacted_meta,
        )
        self.store.append(ev)

        # if secrets detected in metadata before redaction, emit redaction_violation audit event + metric
        if had_secret:
            rv = AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                actor="system",
                action="redaction_violation",
                target=target,
                metadata={"original_action": action},
            )
            self.store.append(rv)
            try:
                if self._metrics:
                    self._metrics.counter_inc("redaction_violations_total", tenant_id=target.get("tenant_id") if target else None, amount=1)
            except Exception:
                pass

        # exporter asynchronously persists events if provided (best-effort)
        try:
            if self.exporter:
                # export just the last appended events (ev and optional rv)
                out = [asdict(e) for e in self.store.list()[-(2 if had_secret else 1):]]
                self.exporter.export(out)
        except Exception:
            pass

    def query(self) -> List[Dict[str, Any]]:
        return [asdict(e) for e in self.store.list()]
