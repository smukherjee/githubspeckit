"""
Tenant context extraction middleware.

Extracts tenant_id from JWT claims and injects TenantContext into request state.
"""

from typing import Callable
from uuid import UUID

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from jose import jwt
from starlette.middleware.base import BaseHTTPMiddleware

from domain.tenants.tenant_context import TenantContext


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract tenant context from JWT and inject into request state.
    
    This runs early in the middleware stack to make tenant_context available
    to all downstream middleware and route handlers.
    
    Constitutional compliance:
    - No business logic (just extraction)
    - Uses domain model TenantContext (hexagonal boundary)
    
    PUBLIC routes (no authentication required):
    - /api/v1/auth/login
    - /api/v1/auth/refresh
    - /health
    - /metrics
    - /docs
    - /redoc
    - /openapi.json
    """
    
    # Define PUBLIC routes that don't require authentication
    # Only health and invitation acceptance endpoints are public per V1.0 spec
    PUBLIC_ROUTES = {
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    # Routes that support public access (no auth token required)
    # These include path patterns that should be checked with startswith()
    PUBLIC_ROUTE_PREFIXES = {
        "/api/v1/invitations/",  # Invitation acceptance is public
        "/static",  # Static files
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Extract tenant context from JWT and inject into request.state.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/route handler
            
        Returns:
            Response from downstream handler
            
        Raises:
            401 Unauthorized if JWT missing (only for protected routes)
            400 Bad Request if tenant_id format invalid
        """
        try:
            # Skip authentication for PUBLIC routes (exact match)
            if request.url.path in self.PUBLIC_ROUTES:
                return await call_next(request)
            
            # Skip authentication for PUBLIC route prefixes (startswith check)
            for prefix in self.PUBLIC_ROUTE_PREFIXES:
                if request.url.path.startswith(prefix):
                    return await call_next(request)
            
            # Extract JWT token from Authorization header
            authorization = request.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Missing or invalid Authorization header"}
                )
            
            token = authorization.split(" ", 1)[1]
            
            # CRITICAL: Must verify JWT signature before extracting claims!
            # Using get_unverified_claims() allows signature forgery attacks.
            # See: CWE-347 (Improper Verification of Cryptographic Signature)
            from adapters.api.deps import get_jwt_service
            
            jwt_service = get_jwt_service()
            
            try:
                # Decode and VERIFY JWT (signature, expiration, issuer, audience)
                payload = jwt_service.decode(token)
            except Exception as e:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": f"Invalid or expired JWT token: {str(e)}"}
                )
            
            # Extract tenant_id and validate format
            tenant_id_str = payload.get("tenant_id")
            if not tenant_id_str:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Missing tenant_id in JWT claims"}
                )
            
            try:
                tenant_id = UUID(tenant_id_str)
            except (ValueError, AttributeError):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": f"Invalid tenant_id format: {tenant_id_str}"}
                )
            
            # Extract user_id (sub claim)
            user_id_str = payload.get("sub")
            if not user_id_str:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Missing sub (user_id) in JWT claims"}
                )
            
            try:
                user_id = UUID(user_id_str)
            except (ValueError, AttributeError):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": f"Invalid user_id format: {user_id_str}"}
                )
            
            # Extract roles
            roles = payload.get("roles", [])
            if isinstance(roles, str):
                roles = [roles]
            
            # Determine if superadmin
            is_superadmin = "superadmin" in roles
            
            # Create TenantContext and inject into request state
            tenant_context = TenantContext(
                tenant_id=tenant_id,
                user_id=user_id,
                roles=tuple(roles),
                is_superadmin=is_superadmin,
                session_tenant_id=None  # Will be set by SessionMiddleware if present
            )
            
            request.state.tenant_context = tenant_context
            
            # Continue to next middleware/handler
            return await call_next(request)
            
        except Exception as e:
            # Catch any unexpected errors
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": f"Error extracting tenant context: {str(e)}"}
            )
