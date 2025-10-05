"""
IMPL-DB-09: Query latency metrics and slow query logging.

Provides:
- SQLAlchemy event listeners for query timing
- Slow query detection and structured logging (FR-034, FR-074)
- Prometheus-compatible latency histogram
- Query classification (SELECT/INSERT/UPDATE/DELETE)

Status: Phase 3 Lane DB-D
Dependencies: SQLAlchemy async engine, observability infrastructure
"""
from __future__ import annotations

import time
import logging
from typing import Any
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

# Structured logger for slow queries
logger = logging.getLogger("infra.persistence.query_metrics")

# Default slow query threshold (milliseconds)
DEFAULT_SLOW_QUERY_THRESHOLD_MS = 100


class QueryMetrics:
    """
    Query performance metrics and slow query detection.
    
    Tracks:
    - Query execution time
    - Query classification (SELECT/INSERT/UPDATE/DELETE)
    - Slow query logging with structured context
    """
    
    def __init__(self, slow_query_threshold_ms: int = DEFAULT_SLOW_QUERY_THRESHOLD_MS):
        """
        Initialize query metrics collector.
        
        Args:
            slow_query_threshold_ms: Threshold for slow query logging (default 100ms per FR-074)
        """
        self.slow_query_threshold_ms = slow_query_threshold_ms
        
        # Metrics storage (placeholder for Prometheus integration)
        # In production, replace with prometheus_client histograms
        self.query_latencies: list[dict[str, Any]] = []
    
    def record_query(
        self,
        query_text: str,
        duration_ms: float,
        query_type: str = "UNKNOWN",
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Record query execution metrics.
        
        Args:
            query_text: SQL query text
            duration_ms: Query execution duration in milliseconds
            query_type: Query classification (SELECT, INSERT, UPDATE, DELETE, DDL)
            context: Optional context (tenant_id, user_id, correlation_id)
        """
        # Record latency
        metric_entry = {
            "duration_ms": duration_ms,
            "query_type": query_type,
            "timestamp": time.time(),
        }
        if context:
            metric_entry.update(context)
        
        self.query_latencies.append(metric_entry)
        
        # Emit slow query log if threshold exceeded (FR-034, FR-074)
        if duration_ms >= self.slow_query_threshold_ms:
            self._log_slow_query(query_text, duration_ms, query_type, context)
    
    def _log_slow_query(
        self,
        query_text: str,
        duration_ms: float,
        query_type: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Emit structured log for slow query (FR-034, FR-074).
        
        Args:
            query_text: SQL query text
            duration_ms: Query execution duration in milliseconds
            query_type: Query classification
            context: Optional context (tenant_id, user_id, correlation_id)
        """
        log_data = {
            "category": "infra.persistence.slow_query",
            "duration_ms": duration_ms,
            "threshold_ms": self.slow_query_threshold_ms,
            "query_type": query_type,
            "query": query_text[:500],  # Truncate to avoid log explosion
        }
        
        if context:
            log_data.update(context)
        
        logger.warning(
            f"Slow query detected: {duration_ms:.2f}ms (threshold: {self.slow_query_threshold_ms}ms)",
            extra=log_data,
        )
    
    def classify_query(self, query_text: str) -> str:
        """
        Classify query by type (SELECT, INSERT, UPDATE, DELETE, DDL).
        
        Args:
            query_text: SQL query text
        
        Returns:
            Query type classification
        """
        query_upper = query_text.strip().upper()
        
        if query_upper.startswith("SELECT"):
            return "SELECT"
        elif query_upper.startswith("INSERT"):
            return "INSERT"
        elif query_upper.startswith("UPDATE"):
            return "UPDATE"
        elif query_upper.startswith("DELETE"):
            return "DELETE"
        elif query_upper.startswith(("CREATE", "ALTER", "DROP", "TRUNCATE")):
            return "DDL"
        elif query_upper.startswith("BEGIN"):
            return "TRANSACTION"
        elif query_upper.startswith("COMMIT"):
            return "COMMIT"
        elif query_upper.startswith("ROLLBACK"):
            return "ROLLBACK"
        else:
            return "UNKNOWN"
    
    def get_latency_percentiles(self, query_type: str | None = None) -> dict[str, float]:
        """
        Calculate latency percentiles for analysis.
        
        Args:
            query_type: Optional filter by query type
        
        Returns:
            Dictionary with p50, p95, p99 latencies in milliseconds
        """
        if not self.query_latencies:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "count": 0}
        
        # Filter by query type if specified
        latencies = [
            entry["duration_ms"]
            for entry in self.query_latencies
            if query_type is None or entry.get("query_type") == query_type
        ]
        
        if not latencies:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "count": 0}
        
        latencies_sorted = sorted(latencies)
        count = len(latencies_sorted)
        
        def percentile(p: float) -> float:
            index = int(p * count)
            if index >= count:
                index = count - 1
            return latencies_sorted[index]
        
        return {
            "p50": percentile(0.50),
            "p95": percentile(0.95),
            "p99": percentile(0.99),
            "count": count,
        }


# Global query metrics instance
_query_metrics: QueryMetrics | None = None


def get_query_metrics() -> QueryMetrics:
    """
    Get global query metrics instance.
    
    Returns:
        QueryMetrics singleton instance
    """
    global _query_metrics
    if _query_metrics is None:
        _query_metrics = QueryMetrics()
    return _query_metrics


def setup_query_instrumentation(
    engine: Engine,
    slow_query_threshold_ms: int = DEFAULT_SLOW_QUERY_THRESHOLD_MS,
) -> None:
    """
    Setup SQLAlchemy event listeners for query instrumentation (FR-034, FR-074).
    
    Instruments:
    - Query execution timing
    - Slow query detection and logging
    - Query classification
    
    Args:
        engine: SQLAlchemy engine to instrument
        slow_query_threshold_ms: Threshold for slow query logging (default 100ms)
    
    Usage:
        engine = create_async_engine(DATABASE_URL)
        setup_query_instrumentation(engine.sync_engine, slow_query_threshold_ms=200)
    """
    global _query_metrics
    _query_metrics = QueryMetrics(slow_query_threshold_ms=slow_query_threshold_ms)
    
    @event.listens_for(engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query start time."""
        context._query_start_time = time.perf_counter()
    
    @event.listens_for(engine, "after_cursor_execute")
    def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query end time and emit metrics."""
        if not hasattr(context, "_query_start_time"):
            return
        
        duration_seconds = time.perf_counter() - context._query_start_time
        duration_ms = duration_seconds * 1000
        
        query_type = _query_metrics.classify_query(statement)
        
        # TODO-OBS-CONTEXT (Phase 4): Extract tenant_id, user_id, correlation_id from context when available
        # For now, basic metrics only
        _query_metrics.record_query(
            query_text=statement,
            duration_ms=duration_ms,
            query_type=query_type,
        )


# TODO (Phase 4): Add Prometheus histogram integration
# from prometheus_client import Histogram
# query_duration_histogram = Histogram(
#     'db_query_duration_seconds',
#     'Database query duration in seconds',
#     ['query_type'],
#     buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0]
# )
