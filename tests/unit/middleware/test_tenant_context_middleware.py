"""
Unit tests for TenantContextMiddleware.

Constitutional Compliance:
- Tests JWT extraction and request state injection
- Validates middleware logic in isolation (mocked FastAPI Request)
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from fastapi import Request, Response
from starlette.datastructures import Headers

from adapters.api.middleware.tenant_context import TenantContextMiddleware
from domain.tenants.tenant_context import TenantContext


@pytest.fixture
def mock_jwt_service():
    """Mock JWT service for testing."""
    service = Mock()
    service.decode = Mock()
    return service


@pytest.fixture
def middleware():
    """Create middleware instance."""
    return TenantContextMiddleware(app=Mock())


@pytest.fixture
def mock_call_next():
    """Mock call_next callable."""
    async def _call_next(request):
        return Response(content=b"OK", status_code=200)
    return _call_next


@pytest.mark.asyncio
async def test_extract_tenant_from_jwt(middleware, mock_jwt_service, mock_call_next):
    """Middleware parses tenant_id from Bearer token and creates TenantContext."""
    tenant_id = uuid4()
    user_id = uuid4()
    
    # Mock JWT payload
    mock_jwt_service.decode.return_value = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "roles": ["user"]
    }
    
    # Create mock request
    request = Request({
        "type": "http",
        "method": "GET",
        "url": "http://test/api/v1/users/me",
        "headers": [[b"authorization", b"Bearer test-token"]],
        "query_string": b"",
        "path": "/api/v1/users/me",
    })
    
    # Patch jwt service
    with patch("adapters.api.deps.get_jwt_service", return_value=mock_jwt_service):
        response = await middleware.dispatch(request, mock_call_next)
    
    # Verify tenant context was injected
    assert hasattr(request.state, "tenant_context")
    context = request.state.tenant_context
    assert isinstance(context, TenantContext)
    assert context.tenant_id == tenant_id
    assert context.user_id == user_id
    assert "user" in context.roles
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_extract_superadmin_role(middleware, mock_jwt_service, mock_call_next):
    """Middleware sets is_superadmin=True when 'superadmin' in JWT roles."""
    tenant_id = uuid4()
    user_id = uuid4()
    
    # Mock JWT payload with superadmin role
    mock_jwt_service.decode.return_value = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "roles": ["superadmin", "user"]
    }
    
    # Create mock request
    request = Request({
        "type": "http",
        "method": "GET",
        "url": "http://test/api/v1/admin/context/tenant",
        "headers": [[b"authorization", b"Bearer test-token"]],
        "query_string": b"",
        "path": "/api/v1/admin/context/tenant",
    })
    
    # Patch jwt service
    with patch("adapters.api.deps.get_jwt_service", return_value=mock_jwt_service):
        response = await middleware.dispatch(request, mock_call_next)
    
    # Verify superadmin flag is set
    assert hasattr(request.state, "tenant_context")
    context = request.state.tenant_context
    assert context.is_superadmin is True
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_inject_request_state(middleware, mock_jwt_service, mock_call_next):
    """Middleware adds tenant_context to request.state for downstream handlers."""
    tenant_id = uuid4()
    user_id = uuid4()
    
    # Mock JWT payload
    mock_jwt_service.decode.return_value = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "roles": ["user"]
    }
    
    # Create mock request
    request = Request({
        "type": "http",
        "method": "GET",
        "url": "http://test/api/v1/users/me",
        "headers": [[b"authorization", b"Bearer test-token"]],
        "query_string": b"",
        "path": "/api/v1/users/me",
    })
    
    # Verify no tenant_context before middleware
    assert not hasattr(request.state, "tenant_context")
    
    # Patch jwt service and dispatch
    with patch("adapters.api.deps.get_jwt_service", return_value=mock_jwt_service):
        await middleware.dispatch(request, mock_call_next)
    
    # Verify tenant_context was injected
    assert hasattr(request.state, "tenant_context")
    assert request.state.tenant_context.tenant_id == tenant_id


@pytest.mark.asyncio
async def test_missing_jwt(middleware, mock_call_next):
    """Middleware returns 401 Unauthorized if Authorization header is missing."""
    # Create mock request without Authorization header
    request = Request({
        "type": "http",
        "method": "GET",
        "url": "http://test/api/v1/users/me",
        "headers": [],
        "query_string": b"",
        "path": "/api/v1/users/me",
    })
    
    response = await middleware.dispatch(request, mock_call_next)
    
    # Verify 401 response
    assert response.status_code == 401
    assert b"Missing or invalid Authorization header" in response.body


@pytest.mark.asyncio
async def test_invalid_tenant_id_format(middleware, mock_jwt_service, mock_call_next):
    """Middleware returns 400 Bad Request if tenant_id is not a valid UUID."""
    user_id = uuid4()
    
    # Mock JWT payload with invalid tenant_id
    mock_jwt_service.decode.return_value = {
        "sub": str(user_id),
        "tenant_id": "invalid-uuid-format",
        "roles": ["user"]
    }
    
    # Create mock request
    request = Request({
        "type": "http",
        "method": "GET",
        "url": "http://test/api/v1/users/me",
        "headers": [[b"authorization", b"Bearer test-token"]],
        "query_string": b"",
        "path": "/api/v1/users/me",
    })
    
    # Patch jwt service
    with patch("adapters.api.deps.get_jwt_service", return_value=mock_jwt_service):
        response = await middleware.dispatch(request, mock_call_next)
    
    # Verify 400 response
    assert response.status_code == 400
    assert b"Invalid tenant_id format" in response.body


@pytest.mark.asyncio
async def test_public_route_skip_authentication(middleware, mock_call_next):
    """Middleware skips authentication for public routes."""
    # Create mock request for public login route
    request = Request({
        "type": "http",
        "method": "POST",
        "url": "http://test/api/v1/auth/login",
        "headers": [],
        "query_string": b"",
        "path": "/api/v1/auth/login",
    })
    
    response = await middleware.dispatch(request, mock_call_next)
    
    # Verify request passes through without authentication
    assert response.status_code == 200
    assert not hasattr(request.state, "tenant_context")
