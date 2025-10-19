"""
Unit tests for SessionMiddleware.

Constitutional Compliance:
- Tests session-based tenant switching for superadmin users
- Validates Redis/cookie backend abstraction
"""

import pytest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json

from adapters.api.middleware.session import SessionMiddleware
from adapters.api.models.session import SessionTenantContext
from domain.tenants.tenant_context import TenantContext


@pytest.fixture
def mock_redis():
    """Mock async Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock()
    return redis


@pytest.fixture
def middleware(mock_redis):
    """Session middleware with mocked Redis."""
    app = Mock()
    return SessionMiddleware(app, redis_client=mock_redis)


@pytest.fixture
def mock_call_next():
    """Mock next middleware/handler."""
    async def call_next(request):
        return Mock(status_code=200)
    return call_next


@pytest.mark.asyncio
async def test_read_session_tenant(middleware, mock_redis):
    """Middleware reads active_tenant_id from Redis session storage."""
    session_id = "test-session-123"
    session_tenant_id = uuid4()
    
    # Mock Redis response
    session_data = {
        "active_tenant_id": str(session_tenant_id),
        "switched_at": datetime.utcnow().isoformat(),
        "previous_tenant_id": str(uuid4())
    }
    mock_redis.get.return_value = json.dumps(session_data).encode('utf-8')
    
    # Read session
    result = await middleware._read_session(session_id)
    
    # Verify
    assert result is not None
    assert result.active_tenant_id == session_tenant_id
    mock_redis.get.assert_called_once_with(f"session:{session_id}:tenant_context")


@pytest.mark.asyncio
async def test_session_not_found(middleware, mock_redis):
    """Middleware returns None if session not found in Redis."""
    session_id = "nonexistent-session"
    
    # Mock Redis returning None
    mock_redis.get.return_value = None
    
    # Read session
    result = await middleware._read_session(session_id)
    
    # Verify
    assert result is None
    mock_redis.get.assert_called_once_with(f"session:{session_id}:tenant_context")


@pytest.mark.asyncio
async def test_inject_session_context(middleware, mock_redis, mock_call_next):
    """Middleware updates request.state.tenant_context.session_tenant_id from session."""
    tenant_id = uuid4()
    user_id = uuid4()
    session_tenant_id = uuid4()
    session_id = "test-session-456"
    
    # Mock Redis response
    session_data = {
        "active_tenant_id": str(session_tenant_id),
        "switched_at": datetime.utcnow().isoformat(),
        "previous_tenant_id": str(tenant_id)
    }
    mock_redis.get.return_value = json.dumps(session_data).encode('utf-8')
    
    # Create mock request with existing tenant_context
    request = Mock()
    request.cookies = {"session_id": session_id}
    request.headers = {}
    request.state = Mock()
    request.state.tenant_context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("superadmin",),
        is_superadmin=True,
        session_tenant_id=None
    )
    
    # Process request through middleware
    await middleware.dispatch(request, mock_call_next)
    
    # Verify session_tenant_id was injected
    assert request.state.tenant_context.session_tenant_id == session_tenant_id


@pytest.mark.asyncio
async def test_cookie_backend_fallback():
    """Middleware uses encrypted cookie if Redis is unavailable (dev mode)."""
    # This test is a placeholder for future cookie backend implementation
    # For now, we'll test that middleware works without Redis
    
    app = Mock()
    middleware = SessionMiddleware(app, redis_client=None, cookie_secret="test-secret")
    
    # Create mock request without session
    request = Mock()
    request.cookies = {}
    request.headers = {}
    request.state = Mock()
    
    async def call_next(req):
        return Mock(status_code=200)
    
    # Should not crash when Redis is None
    response = await middleware.dispatch(request, call_next)
    
    # Verify request passed through without error
    assert response.status_code == 200
