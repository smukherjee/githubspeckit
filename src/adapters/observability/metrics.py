from typing import Dict, Set


class SimpleMetricsRegistry:
    """A tiny in-memory metrics registry for unit tests.

    Tracks known metric names; services can 'register' metrics and increment counters by name.
    """

    REQUIRED_METRICS = {
        "active_users",
        "auth_failures_total",
        "policy_denials_total",
        "rate_limit_hits_total",
        "config_drift_events_total",
        "performance_regressions_total",
        "policy_evaluations_total",
    }

    def __init__(self, prom_adapter=None):
        self.counters: Dict[str, int] = {}
        self.registered: Set[str] = set()
        # optional PromClientAdapter-compatible object
        self.prom = prom_adapter

    def register(self, name: str):
        self.registered.add(name)
        if name not in self.counters:
            self.counters[name] = 0
        # forward to prometheus adapter if present (registering will be implicit when metrics are created)
        try:
            if self.prom:
                # create a counter/gauge on prom side if it's a known metric
                if name.endswith("_total"):
                    self.prom._ensure_counter(name)
                else:
                    # default to gauge for non _total names
                    self.prom._ensure_gauge(name)
        except Exception:
            pass

    def inc(self, name: str, amount: int = 1):
        if name not in self.counters:
            self.register(name)
        self.counters[name] += amount
        # forward increment to prometheus adapter
        try:
            if self.prom:
                # choose counter vs gauge by suffix heuristic
                if name.endswith("_total"):
                    self.prom.counter_inc(name, tenant_id=None, amount=amount)
                else:
                    self.prom.gauge_inc(name, tenant_id=None, amount=amount)
        except Exception:
            pass

    def keys(self):
        return set(self.registered)

    def has_required(self) -> bool:
        return self.REQUIRED_METRICS.issubset(self.registered)

    # Compatibility methods for policy evaluator instrumentation
    def histogram_observe(self, name: str, value: float, tenant_id=None, buckets=None):  # pragma: no cover simple adapter
        # For in-memory tests we don't store histogram data; presence indicates call path works.
        self.register(name)

    def counter_inc(self, name: str, tenant_id=None, amount: int = 1):  # pragma: no cover
        self.inc(name, amount)
