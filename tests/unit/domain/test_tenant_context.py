"""
Unit tests for TenantContext domain model.

Constitutional Compliance:
- Tests domain logic in isolation (no FastAPI/database dependencies)
- Validates hexagonal architecture (Principle I)
"""

import pytest
from uuid import uuid4, UUID

from domain.tenants.tenant_context import TenantContext


def test_effective_tenant_id_standard_user():
    """Standard users always use JWT tenant_id (session_tenant_id ignored)."""
    tenant_id = uuid4()
    user_id = uuid4()
    session_tenant_id = uuid4()  # Different tenant
    
    context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("user",),
        is_superadmin=False,
        session_tenant_id=session_tenant_id
    )
    assert context.effective_tenant_id == tenant_id


def test_effective_tenant_id_superadmin_no_session():
    """Superadmin with no active session uses JWT tenant_id."""
    tenant_id = uuid4()
    user_id = uuid4()
    
    context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("superadmin",),
        is_superadmin=True,
        session_tenant_id=None
    )
    assert context.effective_tenant_id == tenant_id


def test_effective_tenant_id_superadmin_with_session():
    """Superadmin with active session uses session_tenant_id."""
    tenant_id = uuid4()
    user_id = uuid4()
    session_tenant_id = uuid4()  # Different tenant (superadmin switching)
    
    context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("superadmin",),
        is_superadmin=True,
        session_tenant_id=session_tenant_id
    )
    assert context.effective_tenant_id == session_tenant_id


def test_can_access_tenant_superadmin():
    """Superadmin can access any tenant (global scope)."""
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    user_id = uuid4()
    
    context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("superadmin",),
        is_superadmin=True
    )
    assert context.can_access_tenant(other_tenant_id) is True


def test_can_access_tenant_same():
    """User can access their own tenant."""
    tenant_id = uuid4()
    user_id = uuid4()
    
    context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("tenant_admin",),
        is_superadmin=False
    )
    assert context.can_access_tenant(tenant_id) is True


def test_can_access_tenant_cross():
    """Standard user CANNOT access other tenants (isolation enforcement)."""
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    user_id = uuid4()
    
    context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("user",),
        is_superadmin=False
    )
    assert context.can_access_tenant(other_tenant_id) is False
