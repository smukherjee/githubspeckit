"""
Unit tests for TenantAccessPolicy domain model.

Constitutional Compliance:
- Tests authorization logic in isolation (no HTTP/database dependencies)
- Validates tri-state policy engine (Principle III: DENY > ALLOW precedence)
"""

import pytest
from uuid import uuid4, UUID

from domain.tenants.tenant_context import TenantContext
from domain.tenants.policies import TenantAccessPolicy, AccessDecision


def test_evaluate_cross_tenant_superadmin():
    """Superadmin accessing different tenant returns ALLOW with 'superadmin_global_access' rule."""
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    user_id = uuid4()
    
    context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("superadmin",),
        is_superadmin=True
    )
    
    result = TenantAccessPolicy.evaluate_cross_tenant_access(context, other_tenant_id)
    assert result.decision == AccessDecision.ALLOW
    assert result.rule_applied == "superadmin_global_access"


def test_evaluate_cross_tenant_same_tenant():
    """User accessing own tenant returns ALLOW with 'same_tenant_access' rule."""
    tenant_id = uuid4()
    user_id = uuid4()
    
    context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("user",),
        is_superadmin=False
    )
    
    result = TenantAccessPolicy.evaluate_cross_tenant_access(context, tenant_id)
    assert result.decision == AccessDecision.ALLOW
    assert result.rule_applied == "same_tenant_access"


def test_evaluate_cross_tenant_different_tenant():
    """Standard user accessing different tenant returns DENY with 'cross_tenant_isolation' rule."""
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    user_id = uuid4()
    
    context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("user",),
        is_superadmin=False
    )
    
    result = TenantAccessPolicy.evaluate_cross_tenant_access(context, other_tenant_id)
    assert result.decision == AccessDecision.DENY
    assert result.rule_applied == "cross_tenant_isolation"


def test_evaluate_admin_route_superadmin():
    """Superadmin accessing /admin/* routes returns ALLOW with 'superadmin_admin_access' rule."""
    tenant_id = uuid4()
    user_id = uuid4()
    
    context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("superadmin",),
        is_superadmin=True
    )
    
    result = TenantAccessPolicy.evaluate_admin_route_access(context, "/admin/users")
    assert result.decision == AccessDecision.ALLOW
    assert result.rule_applied == "superadmin_admin_access"


def test_evaluate_admin_route_tenant_admin():
    """Tenant admin accessing /admin/* routes returns ALLOW with 'tenant_admin_access' rule."""
    tenant_id = uuid4()
    user_id = uuid4()
    
    context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("tenant_admin",),
        is_superadmin=False
    )
    
    result = TenantAccessPolicy.evaluate_admin_route_access(context, "/admin/users")
    assert result.decision == AccessDecision.ALLOW
    assert result.rule_applied == "tenant_admin_access"


def test_evaluate_admin_route_standard_user():
    """Standard user accessing /admin/* routes returns DENY with 'admin_role_required' rule."""
    tenant_id = uuid4()
    user_id = uuid4()
    
    context = TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=("user",),
        is_superadmin=False
    )
    
    result = TenantAccessPolicy.evaluate_admin_route_access(context, "/admin/users")
    assert result.decision == AccessDecision.DENY
    assert result.rule_applied == "admin_role_required"
