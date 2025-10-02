"""Tracing bootstrap (minimal OpenTelemetry setup with env-driven exporter selection).

Environment Variables:
  OTEL_EXPORTER_OTLP_ENDPOINT - if set, uses OTLP HTTP exporter; else console exporter.
"""
from __future__ import annotations
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
try:  # optional dependency present in pyproject
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # type: ignore
except Exception:  # pragma: no cover - fallback if package not available
    OTLPSpanExporter = None  # type: ignore

_initialized = False


def init_tracing():  # pragma: no cover simple init
    global _initialized
    if _initialized:
        return
    provider = TracerProvider()
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint and OTLPSpanExporter is not None:
        exporter = OTLPSpanExporter(endpoint=endpoint)
    else:
        exporter = ConsoleSpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _initialized = True


def get_tracer(name: str = "app"):
    return trace.get_tracer(name)

__all__ = ["init_tracing", "get_tracer"]
