import os
from pathlib import Path

from services.audit_service import AuditService, InMemoryAuditStore
from adapters.audit.exporter import FileAuditExporter


def test_audit_redaction_and_export(tmp_path):
    store = InMemoryAuditStore()
    export_file = tmp_path / "audit.log"
    exporter = FileAuditExporter(str(export_file))
    svc = AuditService(store=store, exporter=exporter)

    svc.emit(actor="tester", action="user.create", target={"tenant_id": "t-1"}, metadata={"password": "secret"})

    # in-memory store should contain both event and redaction_violation
    events = svc.query()
    assert any(e["action"] == "user.create" for e in events)
    assert any(e["action"] == "redaction_violation" for e in events)

    # exporter file should exist and contain JSON lines
    assert export_file.exists()
    txt = export_file.read_text()
    assert "user.create" in txt
