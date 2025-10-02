import os

def test_tracing_startup_console(monkeypatch):
    # Force console exporter mode (default)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    from adapters.api.app import create_app
    app = create_app()
    # Tracer provider should be set; importing again should not error
    from observability.tracing import get_tracer
    tracer = get_tracer("test")
    span = tracer.start_span("dummy")
    span.end()
    assert app is not None


def test_tracing_startup_otlp(monkeypatch):
    # Simulate OTLP endpoint availability (no real collector needed because exporter just constructs)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    from adapters.api.app import create_app
    app = create_app()
    from observability.tracing import get_tracer
    tracer = get_tracer("test-otlp")
    span = tracer.start_span("dummy-otlp")
    span.end()
    assert app is not None
