"""
Session middleware for superadmin tenant switching.

Manages Redis/cookie-based session storage for active tenant context.
"""

from typing import Callable, Optional
from uuid import UUID
import json

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis

from adapters.api.models.session import SessionTenantContext


class SessionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to read tenant context from session (Redis or cookie).
    
    For superadmins who have switched tenants, this middleware reads
    the active_tenant_id from the session and updates the TenantContext
    that was injected by TenantContextMiddleware.
    
    Constitutional compliance:
    - Depends on TenantContextMiddleware (runs after it)
    - Updates session_tenant_id in existing TenantContext
    """
    
    def __init__(
        self,
        app,
        redis_client: Optional[redis.Redis] = None,
        cookie_secret: Optional[str] = None
    ):
        """
        Initialize session middleware.
        
        Args:
            app: FastAPI application
            redis_client: Optional async Redis client (if None, uses cookie fallback)
            cookie_secret: Secret for encrypting session cookies (dev mode)
        """
        super().__init__(app)
        self.redis_client = redis_client
        self.cookie_secret = cookie_secret
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Read session tenant context and update request.state.tenant_context.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/route handler
            
        Returns:
            Response from downstream handler
        """
        # Check if tenant_context was injected by TenantContextMiddleware
        if not hasattr(request.state, "tenant_context"):
            # TenantContextMiddleware not run or failed - skip session reading
            return await call_next(request)
        
        # Get session ID from cookie or header
        session_id = request.cookies.get("session_id") or request.headers.get("X-Session-Id")
        
        if session_id:
            # Try to read session from Redis
            session_context = await self._read_session(session_id)
            
            if session_context:
                # Update tenant_context with session tenant_id
                # Note: We need to create a new TenantContext since it's frozen (immutable)
                original_context = request.state.tenant_context
                updated_context = type(original_context)(
                    tenant_id=original_context.tenant_id,
                    user_id=original_context.user_id,
                    roles=original_context.roles,
                    is_superadmin=original_context.is_superadmin,
                    session_tenant_id=session_context.active_tenant_id
                )
                request.state.tenant_context = updated_context
        
        # Continue to next middleware/handler
        return await call_next(request)
    
    async def _read_session(self, session_id: str) -> Optional[SessionTenantContext]:
        """
        Read session tenant context from Redis or cookie.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionTenantContext if found, None otherwise
        """
        try:
            if self.redis_client:
                # Try Redis first (async)
                redis_key = f"session:{session_id}:tenant_context"
                value = await self.redis_client.get(redis_key)
                
                if value:
                    # Parse JSON value from Redis
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    
                    # Parse into SessionTenantContext
                    data = json.loads(value)
                    return SessionTenantContext(**data)
            
            # TODO: Implement encrypted cookie fallback for dev mode
            # if self.cookie_secret:
            #     return self._read_encrypted_cookie(session_id)
            
            return None
            
        except Exception as e:
            # Log error but don't fail request
            # In production, use proper logging
            # logger.warning(f"Failed to read session {session_id}: {e}")
            return None
