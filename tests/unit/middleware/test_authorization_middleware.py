"""
Unit tests for AuthorizationMiddleware.

Constitutional Compliance:
- Tests policy enforcement at middleware layer
- Validates RBAC integration with TenantAccessPolicy

Status: Implementation complete (T032), tests updated
"""

import pytest
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, Mock
from fastapi import Request
from starlette.datastructures import URL

from adapters.api.middleware.authorization import AuthorizationMiddleware
from domain.tenants.tenant_context import TenantContext


@pytest.mark.asyncio
async def test_allow_cross_tenant_superadmin():
    """Superadmin can access resources in any tenant (policy allows)."""
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    user_id = uuid4()
    
    # Create mock request with tenant_context for superadmin
    request = Mock(spec=Request)
    request.url = Mock()
    request.url.path = f"/api/v1/tenants/{other_tenant_id}/users"
    request.state = Mock()
    request.state.tenant_context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("superadmin",),
        is_superadmin=True,
        session_tenant_id=None
    )
    
    # Mock call_next to return success
    call_next = AsyncMock(return_value=Mock(status_code=200))
    
    # Execute middleware
    middleware = AuthorizationMiddleware(app=Mock())
    response = await middleware.dispatch(request, call_next)
    
    # Verify policy allowed access
    assert response.status_code == 200
    call_next.assert_awaited_once()


@pytest.mark.asyncio
async def test_deny_cross_tenant_standard_user():
    """Standard user CANNOT access resources in other tenants (policy denies, returns 403)."""
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    user_id = uuid4()
    
    # Create mock request with tenant_context for standard user
    request = Mock(spec=Request)
    request.url = Mock()
    request.url.path = f"/api/v1/tenants/{other_tenant_id}/users"
    request.state = Mock()
    request.state.tenant_context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("user",),
        is_superadmin=False,
        session_tenant_id=None
    )
    
    # Mock call_next (should NOT be called)
    call_next = AsyncMock()
    
    # Execute middleware
    middleware = AuthorizationMiddleware(app=Mock())
    response = await middleware.dispatch(request, call_next)
    
    # Verify policy denied access
    assert response.status_code == 403
    assert "X-Tenant-Isolation-Policy" in response.headers
    assert response.headers["X-Tenant-Isolation-Policy"] == "cross_tenant_isolation"
    call_next.assert_not_awaited()


@pytest.mark.asyncio
async def test_allow_same_tenant():
    """User can access resources in their own tenant (policy allows)."""
    tenant_id = uuid4()
    user_id = uuid4()
    
    # Create mock request with tenant_context for user accessing own tenant
    request = Mock(spec=Request)
    request.url = Mock()
    request.url.path = f"/api/v1/tenants/{tenant_id}/users"
    request.state = Mock()
    request.state.tenant_context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("user",),
        is_superadmin=False,
        session_tenant_id=None
    )
    
    # Mock call_next to return success
    call_next = AsyncMock(return_value=Mock(status_code=200))
    
    # Execute middleware
    middleware = AuthorizationMiddleware(app=Mock())
    response = await middleware.dispatch(request, call_next)
    
    # Verify policy allowed access
    assert response.status_code == 200
    call_next.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_route_superadmin():
    """Superadmin can access /admin/* routes (policy allows)."""
    tenant_id = uuid4()
    user_id = uuid4()
    
    # Create mock request with tenant_context for superadmin
    request = Mock(spec=Request)
    request.url = Mock()
    request.url.path = "/admin/context/tenant"
    request.path_params = {}  # No tenant_id in path
    request.query_params = {}  # No tenant_id in query
    request.state = Mock()
    request.state.tenant_context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("superadmin",),
        is_superadmin=True,
        session_tenant_id=None
    )
    
    # Mock call_next to return success
    call_next = AsyncMock(return_value=Mock(status_code=200))
    
    # Execute middleware
    middleware = AuthorizationMiddleware(app=Mock())
    response = await middleware.dispatch(request, call_next)
    
    # Verify policy allowed access
    assert response.status_code == 200
    call_next.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_route_tenant_admin():
    """Tenant admin can access /admin/* routes (policy allows for tenant_admin role)."""
    tenant_id = uuid4()
    user_id = uuid4()
    
    # Create mock request with tenant_context for tenant_admin
    request = Mock(spec=Request)
    request.url = Mock()
    request.url.path = "/admin/users"
    request.path_params = {}  # No tenant_id in path
    request.query_params = {}  # No tenant_id in query
    request.state = Mock()
    request.state.tenant_context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("tenant_admin",),
        is_superadmin=False,
        session_tenant_id=None
    )
    
    # Mock call_next to return success
    call_next = AsyncMock(return_value=Mock(status_code=200))
    
    # Execute middleware
    middleware = AuthorizationMiddleware(app=Mock())
    response = await middleware.dispatch(request, call_next)
    
    # Verify policy allowed access
    assert response.status_code == 200
    call_next.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_route_denied():
    """Standard user CANNOT access /admin/* routes (policy denies, returns 403)."""
    tenant_id = uuid4()
    user_id = uuid4()
    
    # Create mock request with tenant_context for standard user
    request = Mock(spec=Request)
    request.url = Mock()
    request.url.path = "/admin/tenants"
    request.path_params = {}  # No tenant_id in path
    request.query_params = {}  # No tenant_id in query
    request.state = Mock()
    request.state.tenant_context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("user",),
        is_superadmin=False,
        session_tenant_id=None
    )
    
    # Mock call_next (should NOT be called)
    call_next = AsyncMock()
    
    # Execute middleware
    middleware = AuthorizationMiddleware(app=Mock())
    response = await middleware.dispatch(request, call_next)
    
    # Verify policy denied access
    assert response.status_code == 403
    assert "X-Tenant-Isolation-Policy" in response.headers
    assert response.headers["X-Tenant-Isolation-Policy"] == "admin_role_required"
    call_next.assert_not_awaited()


@pytest.mark.asyncio
async def test_audit_log_created():
    """All policy evaluations trigger audit logging (currently placeholder)."""
    tenant_id = uuid4()
    user_id = uuid4()
    
    # Create mock request with cross-tenant access attempt
    request = Mock(spec=Request)
    request.url = Mock()
    other_tenant_id = uuid4()
    request.url.path = f"/api/v1/tenants/{other_tenant_id}/users"
    request.state = Mock()
    request.state.tenant_context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("user",),
        is_superadmin=False,
        session_tenant_id=None
    )
    
    # Mock call_next (should NOT be called for denied access)
    call_next = AsyncMock()
    
    # Execute middleware
    middleware = AuthorizationMiddleware(app=Mock())
    response = await middleware.dispatch(request, call_next)
    
    # Verify policy was evaluated and decision logged (audit is placeholder, so we just verify policy ran)
    assert response.status_code == 403
    # NOTE: Actual audit logging is placeholder (T056.1) - just verifying policy evaluation occurs
