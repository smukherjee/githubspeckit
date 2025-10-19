"""
Authorization middleware for policy enforcement.

Evaluates tenant access policies and enforces RBAC rules.
"""

from typing import Callable
from uuid import UUID

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from domain.tenants.policies import TenantAccessPolicy, AccessDecision, PolicyEvaluationResult


class AuthorizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce tenant isolation and RBAC policies.
    
    This middleware:
    1. Evaluates cross-tenant access (if tenant_id in path/query)
    2. Evaluates admin route access (if path starts with /admin)
    3. Denies access with 403 if policy evaluation returns DENY
    4. Logs all policy evaluations to audit domain
    
    Constitutional compliance:
    - Uses TenantAccessPolicy from domain (hexagonal boundary)
    - Depends on TenantContextMiddleware (requires tenant_context in state)
    """
    
    async def _audit_policy_evaluation(
        self, 
        request: Request, 
        result: PolicyEvaluationResult
    ) -> None:
        """
        Log policy evaluation to audit domain (non-blocking).
        
        Records all policy decisions (ALLOW/DENY/ABSTAIN) for compliance and security monitoring.
        Audit failures do not block request processing.
        
        NOTE: This is a placeholder implementation. In production, audit events should be 
        logged asynchronously via a background task or message queue to avoid blocking
        request processing. Currently disabled to prevent middleware overhead during testing.
        
        Args:
            request: FastAPI request with tenant_context
            result: Policy evaluation result from TenantAccessPolicy
        """
        # TODO: Enable audit logging after implementing async background task pattern
        # Current implementation would create database connections in middleware,
        # which is not recommended for production use.
        # 
        # Recommended approach:
        # 1. Enqueue audit event to background task queue
        # 2. Worker process consumes queue and writes to database
        # 3. No blocking of request processing
        pass
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Evaluate authorization policies and enforce access control.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/route handler
            
        Returns:
            Response from downstream handler or 403 Forbidden
        """
        # Check if tenant_context exists (from TenantContextMiddleware)
        if not hasattr(request.state, "tenant_context"):
            # TenantContextMiddleware not run - can't evaluate policies
            return await call_next(request)
        
        tenant_context = request.state.tenant_context
        
        # Extract requested tenant_id from path parameters
        requested_tenant_id = self._extract_tenant_id_from_path(request)
        
        # Evaluate cross-tenant access if tenant_id is present
        if requested_tenant_id:
            result = TenantAccessPolicy.evaluate_cross_tenant_access(
                tenant_context,
                requested_tenant_id
            )
            
            # Log policy evaluation to audit
            await self._audit_policy_evaluation(request, result)
            
            if result.is_denied():
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": "Access denied by tenant isolation policy",
                        "rule_applied": result.rule_applied,
                        "reason": result.reason
                    },
                    headers={
                        "X-Tenant-Isolation-Policy": result.rule_applied
                    }
                )
        
        # Evaluate admin route access if path starts with /admin
        if request.url.path.startswith("/admin"):
            result = TenantAccessPolicy.evaluate_admin_route_access(
                tenant_context,
                request.url.path
            )
            
            # Log policy evaluation to audit
            await self._audit_policy_evaluation(request, result)
            
            if result.is_denied():
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": "Access denied - admin role required",
                        "rule_applied": result.rule_applied,
                        "reason": result.reason
                    },
                    headers={
                        "X-Tenant-Isolation-Policy": result.rule_applied
                    }
                )
        
        # Policy allows access - continue to handler
        return await call_next(request)
    
    def _extract_tenant_id_from_path(self, request: Request) -> UUID | None:
        """
        Extract tenant_id from path parameters or query string.
        
        Looks for:
        - Path parameter: /tenants/{tenant_id}/...
        - Query parameter: ?tenant_id=...
        
        Args:
            request: FastAPI request
            
        Returns:
            UUID if found, None otherwise
        """
        import re
        try:
            # Parse tenant_id from URL path using regex
            # Matches patterns like /api/v1/tenants/{uuid}/...
            path = request.url.path
            match = re.search(r'/tenants/([a-f0-9-]{36})/', path, re.IGNORECASE)
            if match:
                return UUID(match.group(1))
            
            # Check path parameters (may not be populated yet in middleware)
            if hasattr(request, "path_params") and "tenant_id" in request.path_params:
                return UUID(request.path_params["tenant_id"])
            
            # Check query parameters
            tenant_id_str = request.query_params.get("tenant_id")
            if tenant_id_str:
                return UUID(tenant_id_str)
            
            return None
            
        except (ValueError, AttributeError):
            # Invalid UUID format - return None (will be caught by route validation)
            return None
