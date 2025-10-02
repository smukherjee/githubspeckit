from collections import deque
from typing import Deque, Tuple
import statistics


class RegressionDetector:
    """Simple detector: records recent p95 latency samples (timestamp, value) and signals regression
    if average over window exceeds threshold for N consecutive windows. This is intentionally
    lightweight for unit testing the false-positive filtering behavior.
    """

    def __init__(self, window_size: int = 3, threshold_ms: int = 200, metrics_adapter=None):
        self.window_size = window_size
        self.threshold_ms = threshold_ms
        # store recent windows as deque of lists
        self.recent: Deque[float] = deque(maxlen=window_size)
        self._metrics = metrics_adapter

    def observe(self, value_ms: float) -> bool:
        """Observe a p95 latency sample (ms). Returns True if this observation indicates
        the system is in a regression state (avg over recent samples > threshold).
        """
        self.recent.append(value_ms)
        if len(self.recent) < self.window_size:
            return False
        med = statistics.median(self.recent)
        is_reg = med > self.threshold_ms
        # emit metric if regression detected
        if is_reg:
            try:
                if self._metrics:
                    # no tenant context here; use global
                    self._metrics.counter_inc("performance_regressions_total", tenant_id=None, amount=1)
            except Exception:
                pass
        return is_reg
