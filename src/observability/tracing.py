"""Tracing bootstrap (minimal OpenTelemetry setup with config-driven exporter selection).

Configuration:
  OTEL_EXPORTER_OTLP_ENDPOINT - if set in descriptor.toml, uses OTLP HTTP exporter; else console.
  
Constitution VII Compliance: All environment access goes through domain.config.settings.
"""
from __future__ import annotations
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter, SpanExporter
try:  # optional dependency present in pyproject
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
except Exception:  # pragma: no cover - fallback if package not available
    OTLPSpanExporter = None  # type: ignore[assignment,misc]

from domain.config.settings import get_observability_settings

_initialized = False


def init_tracing() -> None:  # pragma: no cover simple init
    global _initialized
    if _initialized:
        return
    
    settings = get_observability_settings()
    provider = TracerProvider()
    exporter: SpanExporter
    
    if settings.otel_exporter_otlp_endpoint and OTLPSpanExporter is not None:
        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
    else:
        exporter = ConsoleSpanExporter()
    
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _initialized = True


def get_tracer(name: str = "app") -> trace.Tracer:
    return trace.get_tracer(name)

__all__ = ["init_tracing", "get_tracer"]
