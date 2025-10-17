# Observability Module

## Purpose

This module provides observability infrastructure for the application, including:
- **Tracing**: Distributed tracing using OpenTelemetry
- **Metrics**: Performance and business metrics collection
- **Context Propagation**: Trace context across async boundaries

## Architecture Decision

The `observability/` module is a **cross-cutting concern** that sits outside the hexagonal core but is used by both domain and adapter layers.

### Why Not in `adapters/`?

While observability involves external systems (like Jaeger, Prometheus), placing it in `adapters/observability/` would be misleading:

1. **Not a Port Implementation**: Observability is not an implementation of a domain-defined port. It's infrastructure that instruments *all* layers.

2. **Cross-Layer Usage**: The observability module is imported and used by:
   - Domain layer (business logic tracing)
   - Service layer (use case orchestration)
   - Adapter layer (I/O operation spans)
   - API layer (HTTP request tracing)

3. **Infrastructure, Not Adapter**: This is foundational infrastructure similar to `quality/` and `cli/` that supports the entire application.

### Constitution Compliance (v1.5.1)

**Principle I (Modularity)**: ✅ Observability is a well-defined module with clear boundaries

**Principle II (Hexagonal Architecture)**: ✅ Observability is infrastructure that instruments the hexagon without being part of domain or adapters

**Principle V (Observability)**: ✅ This module implements the tracing and metrics requirements

## Module Structure

```
src/observability/
├── __init__.py              # Public API exports
├── tracer.py                # OpenTelemetry tracer setup
├── metrics.py               # Metrics collection (if implemented)
└── context.py               # Context propagation helpers (if needed)
```

## Usage Example

```python
from observability import get_tracer

tracer = get_tracer(__name__)

async def my_service_method():
    with tracer.start_as_current_span("my_operation"):
        # Your code here
        pass
```

## Related Documentation

- Constitution v1.5.1, Principle V (Observability)
- OpenTelemetry Python Documentation: https://opentelemetry.io/docs/instrumentation/python/
- FR-043: Distributed tracing requirement
