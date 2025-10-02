"""Simple in-memory token bucket rate limiter (SEC lane foundation)."""
from __future__ import annotations
from dataclasses import dataclass
from time import monotonic
from typing import Dict


@dataclass
class Bucket:
    capacity: int
    refill_rate_per_sec: float
    tokens: float
    last: float


class RateLimiter:
    def __init__(self, capacity: int = 20, refill_rate_per_sec: float = 1.0, metrics_adapter=None):
        self.capacity = capacity
        self.refill_rate = refill_rate_per_sec
        self._buckets: Dict[str, Bucket] = {}
        self._metrics = metrics_adapter

    def allow(self, key: str) -> bool:
        now = monotonic()
        b = self._buckets.get(key)
        if not b:
            b = Bucket(self.capacity, self.refill_rate, self.capacity, now)
            self._buckets[key] = b
        # refill
        elapsed = now - b.last
        b.tokens = min(b.capacity, b.tokens + elapsed * b.refill_rate_per_sec)
        b.last = now
        if b.tokens >= 1:
            b.tokens -= 1
            return True
        try:
            if self._metrics:
                self._metrics.counter_inc("rate_limit_hits_total", tenant_id=None, amount=1)
        except Exception:
            pass
        return False

__all__ = ["RateLimiter"]
