"""
Tenant access policy domain service.

Constitutional Compliance:
- Principle III: RBAC + Policy Engine (deny > allow precedence)
- Principle VI: Auth logic reusable (no domain-specific rules here)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from uuid import UUID

from .tenant_context import TenantContext


class AccessDecision(str, Enum):
    """
    Tri-state authorization decision.
    
    ALLOW: Access is explicitly permitted
    DENY: Access is explicitly forbidden
    ABSTAIN: No decision (policy doesn't apply)
    """
    ALLOW = "ALLOW"
    DENY = "DENY"
    ABSTAIN = "ABSTAIN"


@dataclass(frozen=True)
class PolicyEvaluationResult:
    """
    Result of a policy evaluation.
    
    Includes the decision, the rule that was applied, and optional reasoning.
    This is used for audit logging and debugging.
    """
    decision: AccessDecision
    rule_applied: str
    reason: Optional[str] = None
    
    def is_allowed(self) -> bool:
        """Check if this result represents an ALLOW decision."""
        return self.decision == AccessDecision.ALLOW
    
    def is_denied(self) -> bool:
        """Check if this result represents a DENY decision."""
        return self.decision == AccessDecision.DENY


class TenantAccessPolicy:
    """
    Policy engine for tenant isolation and authorization.
    
    Implements the authorization rules defined in spec.md:
    1. Superadmins can access any tenant (global access)
    2. Standard users can only access their own tenant
    3. Cross-tenant access is denied for non-superadmins
    4. Admin routes require superadmin or tenant_admin role
    """
    
    @staticmethod
    def evaluate_cross_tenant_access(
        context: TenantContext,
        requested_tenant_id: UUID
    ) -> PolicyEvaluationResult:
        """
        Evaluate if a context can access resources in the requested tenant.
        
        Rules:
        1. Superadmin → ALLOW (any tenant)
        2. Same tenant → ALLOW
        3. Cross-tenant → DENY
        
        Args:
            context: The tenant context (from JWT + session)
            requested_tenant_id: The tenant being accessed
            
        Returns:
            PolicyEvaluationResult with decision and rule applied
        """
        # Rule 1: Superadmin global access
        if context.is_superadmin:
            return PolicyEvaluationResult(
                decision=AccessDecision.ALLOW,
                rule_applied="superadmin_global_access",
                reason="Superadmin role grants access to all tenants"
            )
        
        # Rule 2: Same tenant access
        if context.effective_tenant_id == requested_tenant_id:
            return PolicyEvaluationResult(
                decision=AccessDecision.ALLOW,
                rule_applied="same_tenant_access",
                reason="User accessing their own tenant"
            )
        
        # Rule 3: Cross-tenant isolation
        return PolicyEvaluationResult(
            decision=AccessDecision.DENY,
            rule_applied="cross_tenant_isolation",
            reason=f"User from tenant {context.effective_tenant_id} cannot access tenant {requested_tenant_id}"
        )
    
    @staticmethod
    def evaluate_admin_route_access(
        context: TenantContext,
        route_path: str
    ) -> PolicyEvaluationResult:
        """
        Evaluate if a context can access admin routes (/admin/*).
        
        Rules:
        1. Superadmin → ALLOW
        2. Tenant admin → ALLOW
        3. Standard user → DENY
        
        Args:
            context: The tenant context (from JWT + session)
            route_path: The route being accessed (e.g., "/admin/users")
            
        Returns:
            PolicyEvaluationResult with decision and rule applied
        """
        # Rule 1: Superadmin access
        if context.is_superadmin:
            return PolicyEvaluationResult(
                decision=AccessDecision.ALLOW,
                rule_applied="superadmin_admin_access",
                reason="Superadmin role grants access to all admin routes"
            )
        
        # Rule 2: Tenant admin access
        if "tenant_admin" in context.roles:
            return PolicyEvaluationResult(
                decision=AccessDecision.ALLOW,
                rule_applied="tenant_admin_access",
                reason="Tenant admin role grants access to admin routes"
            )
        
        # Rule 3: Standard user denied
        return PolicyEvaluationResult(
            decision=AccessDecision.DENY,
            rule_applied="admin_role_required",
            reason=f"User with roles {context.roles} lacks required admin role"
        )
