"""RBAC validation helpers for cross-tenant access control.

Provides reusable validation functions for multi-tenant RBAC enforcement.
"""
from __future__ import annotations

from fastapi import HTTPException

from adapters.api.auth_deps import AuthenticatedUser


def validate_cross_tenant_access(
    current_user: AuthenticatedUser,
    resource_tenant_id: str,
    operation: str
) -> None:
    """Validate cross-tenant access for an operation (FR-091).
    
    **Rule**: Only superadmin users can perform operations across tenants.
    Non-superadmin users are restricted to their own tenant.
    
    Args:
        current_user: Currently authenticated user
        resource_tenant_id: Tenant ID of the resource being accessed
        operation: Description of the operation (for error message)
        
    Raises:
        HTTPException: 403 Forbidden if cross-tenant access attempted by non-superadmin
        
    Examples:
        >>> validate_cross_tenant_access(current_user, "tenant-123", "user creation")
        >>> # Raises 403 if current_user.tenant_id != "tenant-123" and not superadmin
    """
    # Superadmin can access any tenant
    if current_user.is_superadmin():
        return
    
    # Non-superadmin must match tenant_id
    if current_user.tenant_id != resource_tenant_id:
        raise HTTPException(
            status_code=403,
            detail=f"Cross-tenant {operation} requires superadmin role. "
                   f"Your tenant: {current_user.tenant_id}, "
                   f"Resource tenant: {resource_tenant_id}"
        )


def validate_role_assignment(
    current_user: AuthenticatedUser,
    target_role: str
) -> None:
    """Validate role assignment permissions (FR-093, FR-094).
    
    **Rules**:
    - Superadmin: Cannot be assigned via API (bootstrap only)
    - Tenant_admin: Can assign developer, analyst, user, service_account, support_readonly
    - Other roles: Cannot assign roles
    
    Args:
        current_user: Currently authenticated user
        target_role: Role being assigned to another user
        
    Raises:
        HTTPException: 403 Forbidden if role assignment not permitted
        
    Examples:
        >>> validate_role_assignment(tenant_admin_user, "developer")  # OK
        >>> validate_role_assignment(tenant_admin_user, "superadmin")  # Raises 403
        >>> validate_role_assignment(regular_user, "user")  # Raises 403
    """
    # Rule 1: Superadmin role cannot be assigned via API
    if target_role == "superadmin":
        raise HTTPException(
            status_code=403,
            detail="Superadmin role cannot be assigned via API. "
                   "Superadmin users must be created via bootstrap process."
        )
    
    # Rule 2: Superadmin can assign any role (except superadmin, caught above)
    if current_user.is_superadmin():
        return
    
    # Rule 3: Tenant_admin can assign specific roles
    if current_user.has_role("tenant_admin"):
        assignable_roles = {
            "developer",
            "analyst",
            "user",
            "service_account",
            "support_readonly"
        }
        
        if target_role not in assignable_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Tenant_admin cannot assign role '{target_role}'. "
                       f"Allowed roles: {', '.join(sorted(assignable_roles))}"
            )
        return
    
    # Rule 4: Non-tenant_admin cannot assign roles
    raise HTTPException(
        status_code=403,
        detail="Only tenant_admin and superadmin users can assign roles"
    )


def validate_tenant_isolation(
    current_user: AuthenticatedUser,
    resource_tenant_id: str | None
) -> str:
    """Enforce tenant isolation for non-superadmin users (FR-090).
    
    **Automatic Tenant Filtering**:
    - Superadmin: Can query any tenant (returns resource_tenant_id as-is or None for all)
    - Non-superadmin: Automatically filtered to own tenant (ignores resource_tenant_id)
    
    Args:
        current_user: Currently authenticated user
        resource_tenant_id: Requested tenant ID (may be None for "all tenants")
        
    Returns:
        Effective tenant ID to use for query (current_user.tenant_id for non-superadmin)
        
    Examples:
        >>> tenant_id = validate_tenant_isolation(regular_user, "other-tenant")
        >>> # Returns: regular_user.tenant_id (ignores "other-tenant")
        
        >>> tenant_id = validate_tenant_isolation(superadmin_user, "other-tenant")
        >>> # Returns: "other-tenant" (honors request)
    """
    # Superadmin can access any tenant
    if current_user.is_superadmin():
        return resource_tenant_id or current_user.tenant_id
    
    # Non-superadmin: Always use own tenant_id (automatic filtering)
    return current_user.tenant_id
