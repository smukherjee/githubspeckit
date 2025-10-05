"""Quality metrics collector (IMPL-SEC-06).

Exposes a simple interface to record code/test quality signals. For now, we simulate
collection so tests can assert metric presence via PromClientAdapter.
"""
from __future__ import annotations

from adapters.observability.prometheus_client_adapter import PromClientAdapter

class QualityMetrics:
    REQUIRED = ["quality_gates_fail_total", "justifications_count"]

    def __init__(self, prom: PromClientAdapter):
        self._prom = prom
        # Pre-create counters
        for name in self.REQUIRED:
            if name.endswith("_total"):
                self._prom.counter_inc(name, amount=0)
            else:
                self._prom.gauge_set(name, value=0)

    def record_gate_failure(self, tenant_id: str | None = None) -> None:
        self._prom.counter_inc("quality_gates_fail_total", tenant_id=tenant_id, amount=1)

    def set_justifications(self, count: int) -> None:
        self._prom.gauge_set("justifications_count", value=count)

__all__ = ["QualityMetrics"]
