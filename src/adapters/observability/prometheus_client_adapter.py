from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from typing import Dict


class PromClientAdapter:
    """Adapter that exposes prometheus_client Counters and Gauges with tenant label support.

    Services can call .counter_inc(name, tenant_id) or .gauge_inc/gauge_dec/gauge_set(name, tenant_id, value).
    The adapter creates metrics with a `tenant_id` label and defaults tenant to `_global` when None.
    """

    # canonical metrics (from spec C-030)
    REQUIRED_METRICS = {
        "active_users": "gauge",
        "auth_failures_total": "counter",
        "policy_denials_total": "counter",
        "rate_limit_hits_total": "counter",
        "config_drift_events_total": "counter",
        "performance_regressions_total": "counter",
    }

    def __init__(self, registry: CollectorRegistry | None = None):
        self.registry = registry or CollectorRegistry()
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}

        # Pre-create canonical metrics
        for name, mtype in self.REQUIRED_METRICS.items():
            if mtype == "counter":
                self._ensure_counter(name)
            elif mtype == "gauge":
                self._ensure_gauge(name)

    def _ensure_counter(self, name: str) -> Counter:
        if name in self._counters:
            return self._counters[name]
        c = Counter(name, f"Auto-generated metric {name}", labelnames=("tenant_id",), registry=self.registry)
        self._counters[name] = c
        return c

    def _ensure_gauge(self, name: str) -> Gauge:
        if name in self._gauges:
            return self._gauges[name]
        g = Gauge(name, f"Auto-generated gauge {name}", labelnames=("tenant_id",), registry=self.registry)
        self._gauges[name] = g
        return g

    def _ensure_histogram(self, name: str, buckets=None) -> Histogram:
        if name in self._histograms:
            return self._histograms[name]
        if buckets is None:  # default latency-focused buckets (ms)
            buckets = (0.5, 1, 5, 10, 25, 50, 100, 150, 200, 300, 500, 750, 1000)
        h = Histogram(name, f"Auto-generated histogram {name}", labelnames=("tenant_id",), registry=self.registry, buckets=buckets)
        self._histograms[name] = h
        return h

    def counter_inc(self, name: str, tenant_id: str | None = None, amount: int = 1):
        tenant_label = tenant_id or "_global"
        c = self._ensure_counter(name)
        c.labels(tenant_label).inc(amount)

    def gauge_inc(self, name: str, tenant_id: str | None = None, amount: int = 1):
        tenant_label = tenant_id or "_global"
        g = self._ensure_gauge(name)
        g.labels(tenant_label).inc(amount)

    def gauge_dec(self, name: str, tenant_id: str | None = None, amount: int = 1):
        tenant_label = tenant_id or "_global"
        g = self._ensure_gauge(name)
        g.labels(tenant_label).dec(amount)

    def gauge_set(self, name: str, tenant_id: str | None = None, value: float = 0.0):
        tenant_label = tenant_id or "_global"
        g = self._ensure_gauge(name)
        g.labels(tenant_label).set(value)

    def histogram_observe(self, name: str, value: float, tenant_id: str | None = None, buckets=None):
        tenant_label = tenant_id or "_global"
        h = self._ensure_histogram(name, buckets=buckets)
        h.labels(tenant_label).observe(value)

    def generate_latest(self) -> bytes:
        return generate_latest(self.registry)


__all__ = ["PromClientAdapter"]
