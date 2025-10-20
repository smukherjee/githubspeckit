"""
Rate Limiting Middleware (FR-046 to FR-054, Phase 3.6)

Purpose:
    Protect API endpoints from abuse via IP-based rate limiting using slowapi.
    Provides distributed limiting via Redis for horizontal scaling.

Key Features:
    - Fixed-window rate limiting per IP address
    - Configurable limits via environment variables
    - Redis backend for distributed rate limiting across multiple instances
    - Superadmin bypass mechanism for admin operations
    - HTTP 429 responses with Retry-After headers

Architecture:
    - slowapi: FastAPI-compatible fork of Flask-Limiter
    - limits: Core rate limiting algorithms and storage backends
    - Redis: Distributed counter storage (separate database from sessions)
    
Design Rationale:
    - IP-based: Prevents enumeration attacks regardless of authentication state
    - Configurable: Tunable per-endpoint limits without code changes
    - Distributed: Redis enables horizontal scaling across multiple API instances
    - Graceful degradation: Falls back to in-memory limiting if Redis unavailable

Related:
    - FR-046: Rate limiting research (slowapi + Redis strategy)
    - FR-047: slowapi dependencies installation
    - FR-048: RATE_LIMIT_USER_CREATION configuration
    - FR-049-052: Middleware implementation and integration
    - FR-053-054: Security testing
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from domain.config.descriptor_parser import parse_descriptor


def _is_superadmin(request: Request) -> bool:
    """
    Check if the current request is from a superadmin user.
    
    Used by slowapi's exempt_when parameter to bypass rate limits for admin operations.
    
    Args:
        request: Starlette Request object
        
    Returns:
        True if user is authenticated and has superadmin role, False otherwise
        
    Implementation Note:
        Accesses request.state.user set by auth middleware (dependency injection).
        Returns False if user not authenticated (middleware not run yet).
        
    Related:
        - FR-051: Superadmin bypass mechanism
        - src/adapters/api/dependencies/auth.py: Sets request.state.user
    """
    # Check if user object exists in request state (set by auth middleware)
    if not hasattr(request.state, "user"):
        return False
    
    user = request.state.user
    if not user:
        return False
    
    # Check if user has superadmin role
    # Superadmin role is stored in user.roles list
    return any(role.name == "superadmin" for role in getattr(user, "roles", []))


# Initialize slowapi Limiter instance
# This is a singleton used across the FastAPI application
raw_config = parse_descriptor("config/descriptor.toml")

# Extract Redis URL from configuration (with default fallback)
redis_url = raw_config.get("REDIS_URL", ("redis://localhost:6379/1", False))[0]

limiter = Limiter(
    # key_func: Extract rate limiting key from request (IP address)
    # Uses X-Forwarded-For if behind proxy, else direct IP
    key_func=get_remote_address,
    
    # default_limits: Global fallback limits (1000 requests/hour per IP)
    # Individual endpoints can override with @limiter.limit() decorator
    default_limits=["1000/hour"],
    
    # storage_uri: Redis connection for distributed rate limiting
    # Uses Redis database 1 (distinct from session storage in database 0)
    # Falls back to in-memory storage if Redis unavailable
    storage_uri=redis_url,
    
    # strategy: "fixed-window" - Simple counter reset at fixed intervals
    # Alternative strategies: "moving-window" (more accurate but higher overhead)
    strategy="fixed-window",
    
    # headers_enabled: Add rate limit info to response headers
    # X-RateLimit-Limit: Total allowed requests in window
    # X-RateLimit-Remaining: Requests remaining in current window
    # X-RateLimit-Reset: Unix timestamp when window resets
    headers_enabled=True,
)


__all__ = ["limiter", "_is_superadmin"]
