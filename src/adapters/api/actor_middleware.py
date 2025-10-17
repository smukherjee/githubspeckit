"""
Actor Tracking Middleware (Constitution III & V Compliance).

Extracts actor_user_id from JWT token and stores in request.state for audit logging.
This enables all audit events to track which user performed the action.
"""
from __future__ import annotations

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class ActorTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and store actor_user_id from JWT token.
    
    Sets request.state.user_id for use by audit service dependency.
    Does not enforce authentication (that's done by route dependencies).
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Extract actor ID from Authorization header if present."""
        # Initialize user_id to None (unauthenticated request)
        request.state.user_id = None
        
        # Try to extract from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            try:
                # Decode JWT to get user_id (sub claim)
                # Note: We don't validate the token here - that's done by get_current_user
                # We just extract the subject for audit logging
                from adapters.api.deps import get_jwt_service
                jwt_service = get_jwt_service()
                claims = jwt_service.decode(token)
                request.state.user_id = claims.get("sub")
            except Exception:
                # Invalid token - leave user_id as None
                # Authentication will be enforced by route dependencies
                pass
        
        response = await call_next(request)
        return response


__all__ = ["ActorTrackingMiddleware"]
