"""
Deprecation warning middleware for backward compatibility.

Detects usage of deprecated query parameters and responds with warning headers.
"""

import logging
from datetime import datetime, timezone
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger(__name__)


class DeprecationWarningMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle deprecated tenant_id query parameter.
    
    Behavior:
    1. Detect: Check for ?tenant_id= in query parameters
    2. Before sunset: Log warning + add Deprecation headers
    3. After sunset: Return 400 Bad Request
    
    Constitutional compliance:
    - Backward compatibility window (FR-004)
    - Sunset date from config/descriptor.toml
    """
    
    def __init__(self, app, sunset_date: str = "2025-11-19"):
        """
        Initialize deprecation middleware.
        
        Args:
            app: FastAPI application
            sunset_date: ISO 8601 date string when feature will be removed
        """
        super().__init__(app)
        # Parse sunset date
        self.sunset_date = datetime.fromisoformat(sunset_date).replace(tzinfo=timezone.utc)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Check for deprecated query parameters and respond appropriately.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/route handler
            
        Returns:
            Response with deprecation headers or 400 error
        """
        # Check if tenant_id query parameter is present
        tenant_id_param = request.query_params.get("tenant_id")
        
        if tenant_id_param:
            current_date = datetime.now(timezone.utc)
            
            # Check if sunset date has passed
            if current_date >= self.sunset_date:
                # Sunset has passed - reject request
                logger.error(
                    f"Rejected request with deprecated tenant_id query param (sunset: {self.sunset_date.date()})",
                    extra={
                        "path": request.url.path,
                        "client_ip": request.client.host if request.client else None,
                        "sunset_date": self.sunset_date.isoformat()
                    }
                )
                
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "detail": "The tenant_id query parameter is no longer supported",
                        "sunset_date": self.sunset_date.date().isoformat(),
                        "migration": "Use JWT tenant_id claim instead of query parameter"
                    }
                )
            
            # Sunset not yet passed - log warning and add headers
            logger.warning(
                f"Deprecated tenant_id query param used on {request.url.path}",
                extra={
                    "path": request.url.path,
                    "tenant_id": tenant_id_param,
                    "sunset_date": self.sunset_date.date().isoformat(),
                    "client_ip": request.client.host if request.client else None
                }
            )
            
            # Continue processing request
            response = await call_next(request)
            
            # Add deprecation headers to response
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = self.sunset_date.date().isoformat()
            response.headers["Link"] = '<https://docs.example.com/migration>; rel="deprecation"'
            
            return response
        
        # No deprecated parameters - continue normally
        return await call_next(request)
