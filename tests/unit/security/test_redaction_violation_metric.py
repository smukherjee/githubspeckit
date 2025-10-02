"""TEST-SEC-15: Redaction violation metric & audit emission (FR-073 C-048)."""
from services.audit_service import AuditService, InMemoryAuditStore
from adapters.observability.prometheus_client_adapter import PromClientAdapter
import re


def test_redaction_violation_metric_and_audit():
    prom = PromClientAdapter()
    store = InMemoryAuditStore()
    svc = AuditService(store=store, metrics_adapter=prom)
    svc.emit(actor="u1", action="user.update", target={"tenant_id": "t1"}, metadata={"password": "secret123"})
    actions = [e.action for e in store.list()]
    assert "redaction_violation" in actions, "Expected redaction_violation audit event"
    exposition = prom.generate_latest().decode()
    assert re.search(r"^redaction_violations_total", exposition, re.MULTILINE), "Metric not emitted"
