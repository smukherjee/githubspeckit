"""Superadmin misuse monitor implementing TEST-SEC-17 / IMPL-SEC-18."""
from __future__ import annotations

class SuperadminMisuseMonitor:
    def __init__(self, threshold: int = 10):
        self.threshold = threshold
        self._count = 0
        self._alerted = False

    def record_cross_tenant_action(self, actor: str, action: str, tenant_id: str) -> bool:  # noqa: D401
        if self._alerted:
            return True
        self._count += 1
        if self._count >= self.threshold:
            self._alerted = True
            return True
        return False


__all__ = ["SuperadminMisuseMonitor"]
