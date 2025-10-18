"""Security headers middleware for OWASP compliance.

Implements HTTP security headers to prevent common vulnerabilities:
- Cache-Control: Prevents sensitive data caching
- X-Content-Type-Options: Prevents MIME sniffing attacks
- X-Frame-Options: Prevents clickjacking
- X-XSS-Protection: Legacy XSS protection for older browsers

Addresses:
- OWASP A01:2021 – Broken Access Control
- CWE-525: Use of Web Browser Cache Containing Sensitive Information
- CWE-693: Protection Mechanism Failure
"""
from __future__ import annotations

from starlette.datastructures import Headers
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses per OWASP guidelines.
    
    This middleware implements defense-in-depth security headers:
    
    1. Cache-Control: Prevents browser/proxy caching of sensitive data
       - Sensitive endpoints: no-store, no-cache, must-revalidate, private
       - Public endpoints: Appropriate caching allowed
       
    2. Additional security headers (all responses):
       - X-Content-Type-Options: nosniff (prevent MIME sniffing)
       - X-Frame-Options: DENY (prevent clickjacking)
       - X-XSS-Protection: 1; mode=block (legacy browser protection)
    
    Sensitive Paths:
    - /api/v1/auth/* - Authentication tokens
    - /api/v1/users/* - User personal data
    - /api/v1/policies/* - Authorization rules
    - /api/v1/audit/* - Audit logs
    - /api/v1/tenants/* - Tenant configuration
    - /api/v1/feature-flags/* - Feature toggles
    - /api/v1/invitations/* - Invitation tokens
    - /api/v1/profile/* - User profiles (feature 003)
    
    Cacheable Paths:
    - /health - Health check endpoint
    - /docs - API documentation
    - /openapi.json - OpenAPI schema
    - /static/* - Static assets
    """
    
    # Endpoints that should NEVER be cached (sensitive data)
    SENSITIVE_PATHS: set[str] = {
        "/api/v1/auth",
        "/api/v1/users",
        "/api/v1/policies",
        "/api/v1/audit",
        "/api/v1/tenants",
        "/api/v1/feature-flags",
        "/api/v1/invitations",
        "/api/v1/profile",  # User profile photos (feature 003)
    }
    
    # Static assets that CAN be cached (public, non-sensitive)
    CACHEABLE_PATHS: set[str] = {
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/static/",
    }
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request and add security headers to response.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response with security headers added
        """
        # Process request through next middleware/handler
        response = await call_next(request)
        
        # Determine cache policy based on path
        path = request.url.path
        is_sensitive = self._is_sensitive_path(path)
        is_cacheable = self._is_cacheable_path(path)
        
        if is_sensitive:
            # OWASP recommendation: Prevent ALL caching for sensitive data
            # no-store: Must not be stored in any cache
            # no-cache: Must revalidate with server before using cached copy
            # must-revalidate: Cache must verify with server after expiration
            # private: Only browser cache, not shared/proxy caches
            # max-age=0: Immediately stale
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, private, max-age=0"
            )
            
            # HTTP/1.0 compatibility: Pragma header
            response.headers["Pragma"] = "no-cache"
            
            # Explicit expiration in the past
            response.headers["Expires"] = "0"
            
        elif not is_cacheable:
            # Non-sensitive API endpoints: Allow short-term private caching
            # private: Only browser cache (not proxy)
            # max-age=60: Cache for 60 seconds
            response.headers["Cache-Control"] = "private, max-age=60"
        
        # Cacheable static assets: Use default caching or existing headers
        # (no modification needed)
        
        # Additional security headers (ALL responses, defense in depth)
        self._add_defense_in_depth_headers(response)
        
        return response
    
    def _is_sensitive_path(self, path: str) -> bool:
        """Check if path contains sensitive data requiring no-cache.
        
        Args:
            path: Request URL path
            
        Returns:
            True if path is sensitive (auth, user data, policies, etc.)
        """
        # Strip query parameters (everything after ?)
        path_without_query = path.split("?")[0]
        
        # Check if path starts with any sensitive path
        return any(path_without_query.startswith(sensitive) for sensitive in self.SENSITIVE_PATHS)
    
    def _is_cacheable_path(self, path: str) -> bool:
        """Check if path is public and cacheable.
        
        Args:
            path: Request URL path
            
        Returns:
            True if path is public documentation or static assets
        """
        return any(path.startswith(cacheable) for cacheable in self.CACHEABLE_PATHS)
    
    def _add_defense_in_depth_headers(self, response: Response) -> None:
        """Add additional security headers for defense in depth.
        
        These headers provide protection against various attack vectors:
        - MIME sniffing attacks
        - Clickjacking
        - XSS (legacy browsers)
        - Spectre-like side-channel attacks
        
        Args:
            response: Response to add headers to (modified in place)
        """
        # Prevent MIME type sniffing
        # Browsers must respect Content-Type, not guess based on content
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking attacks
        # Page cannot be embedded in <iframe>, <frame>, <embed>, <object>
        response.headers["X-Frame-Options"] = "DENY"
        
        # Legacy XSS protection for older browsers
        # Modern browsers use CSP, but this helps IE/Edge legacy
        # 1; mode=block: Enable filter and block page if attack detected
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Prevent cross-origin reads via Spectre-like side-channel attacks
        # Only allow same-origin requests to read this resource
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
