"""
Middleware components for tenant context security.

This module provides FastAPI middleware for:
- Tenant context extraction from JWT
- Authorization policy enforcement
- Session-based tenant switching
"""

# Import correlation middleware from parent module (renamed from middleware.py to correlation_middleware.py)
from adapters.api.correlation_middleware import CorrelationMiddleware

# Import new tenant security middleware (Phase 3.3 - T030-T033)
from .tenant_context import TenantContextMiddleware
from .authorization import AuthorizationMiddleware
from .session import SessionMiddleware
from .deprecation_warning import DeprecationWarningMiddleware

__all__ = [
    "CorrelationMiddleware",
    "TenantContextMiddleware",
    "AuthorizationMiddleware",
    "SessionMiddleware",
    "DeprecationWarningMiddleware",
]
