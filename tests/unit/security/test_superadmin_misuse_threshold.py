"""TEST-SEC-17: Superadmin misuse threshold alert (FR-002 C-040).

Simulates repeated cross-tenant actions to trigger alert emission.
"""
from quality.superadmin_misuse_monitor import SuperadminMisuseMonitor


def test_superadmin_misuse_threshold_alert():
    monitor = SuperadminMisuseMonitor(threshold=3)
    alerts = []
    for i in range(3):
        triggered = monitor.record_cross_tenant_action(actor="admin", action=f"act{i}", tenant_id="tA")
    # After threshold actions we expect an alert flag
    assert triggered is True, "Misuse threshold should trigger alert"
    # Confirm subsequent action continues to signal or resets per design (we expect sticky True)
    again = monitor.record_cross_tenant_action(actor="admin", action="actX", tenant_id="tB")
    assert again is True
