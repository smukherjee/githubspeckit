"""Structured logging middleware (TEST-OBS-01 / IMPL-OBS-02 partial).

Provides per-request structured log records with base fields required by constitution:
  - ts (ISO8601 UTC)
  - level
  - msg
  - http_method
  - path
  - status_code
  - duration_ms
  - tenant_id (if resolvable from header X-Tenant-ID)
  - correlation_id (placeholder; will be populated once correlation middleware lands)

Redaction: headers/body keys included in REDACT_KEYS are redacted.

The middleware appends log dicts to an in-memory sink for test assertions. In real deployment
this would integrate with a logging backend (e.g., structlog + OTEL). Keeping minimal for Phase 2.
"""
from __future__ import annotations

import time
from opentelemetry import trace
from datetime import datetime, timezone
from typing import Callable, Awaitable, Dict, Any, List

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .redaction import redact_dict


class InMemoryStructuredLogSink:
    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def emit(self, record: Dict[str, Any]):
        self.records.append(record)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, sink: InMemoryStructuredLogSink | None = None):
        super().__init__(app)
        self.sink = sink or InMemoryStructuredLogSink()

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]):
        start = time.perf_counter()
        tenant_id = request.headers.get("X-Tenant-ID")
        # correlation id placeholder (will integrate with correlation middleware later)
        correlation_id = request.headers.get("X-Correlation-ID") or "pending"

        response: Response | None = None
        exc: Exception | None = None
        try:
            response = await call_next(request)
        except Exception as e:  # noqa: PIE786 broad capture
            exc = e
        finally:
            status_code = response.status_code if response is not None else 500
            duration_ms = (time.perf_counter() - start) * 1000.0
            # Trace context extraction (if any)
            current_span = trace.get_current_span()
            span_ctx = current_span.get_span_context() if current_span else None
            trace_id = (
                f"{span_ctx.trace_id:032x}" if span_ctx and span_ctx.trace_id else None
            )
            span_id = (
                f"{span_ctx.span_id:016x}" if span_ctx and span_ctx.span_id else None
            )
            base = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "level": "info",
                "msg": "request",
                "http_method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "trace_id": trace_id,
                "span_id": span_id,
            }
            # redact potentially sensitive inbound headers subset
            hdrs = {k.lower(): v for k, v in request.headers.items()}
            redacted_headers, had_secret = redact_dict(hdrs)
            base["had_redaction"] = had_secret
            base["headers"] = redacted_headers
            self.sink.emit(base)
        if exc:
            raise exc
        return response  # type: ignore[return-value]


__all__ = [
    "StructuredLoggingMiddleware",
    "InMemoryStructuredLogSink",
]
