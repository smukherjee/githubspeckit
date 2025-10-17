"""TEST-XCUT-11 Span coverage for all API routes.
Verifies that a tracing span list is populated after a request. Placeholder failing test.
"""
import pytest
from fastapi.testclient import TestClient
from adapters.api.app import create_app


def test_tracing_span_capture_placeholder():
    app = create_app()
    client = TestClient(app)
    client.get("/api/v1/health")
    spans = getattr(app.state, "_test_spans", [])
    assert spans, "Expected tracing spans collected (failing until instrumentation stores spans)"
