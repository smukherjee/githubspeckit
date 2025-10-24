"""Permission model and constants for RBAC (FR-122)."""

from enum import Enum
from typing import Final


class Permission(str, Enum):
    """Permission constants for RBAC system.
    
    Permissions use namespace:action format (e.g., 'users:create').
    Special permission '*' grants all permissions (superadmin only).
    """
    
    # Wildcard permission (superadmin only)
    ALL = "*"
    
    # Tenant management
    TENANT_READ = "tenant:read"
    TENANT_UPDATE = "tenant:update"
    TENANT_DELETE = "tenant:delete"
    TENANT_ALL = "tenant:*"
    
    # User management
    USERS_CREATE = "users:create"
    USERS_READ = "users:read"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"
    USERS_READ_OWN = "users:read_own"
    USERS_ALL = "users:*"
    
    # Role management
    ROLES_CREATE = "roles:create"
    ROLES_READ = "roles:read"
    ROLES_UPDATE = "roles:update"
    ROLES_DELETE = "roles:delete"
    ROLES_ALL = "roles:*"
    
    # Policy management
    POLICIES_CREATE = "policies:create"
    POLICIES_READ = "policies:read"
    POLICIES_UPDATE = "policies:update"
    POLICIES_DELETE = "policies:delete"
    POLICIES_ALL = "policies:*"
    
    # Profile management
    PROFILE_UPDATE_OWN = "profile:update_own"
    PROFILE_READ_OWN = "profile:read_own"
    
    # Audit log access
    AUDIT_READ = "audit:read"
    AUDIT_READ_OWN = "audit:read_own"
    
    # Feature flags
    FEATURE_FLAGS_CREATE = "feature_flags:create"
    FEATURE_FLAGS_READ = "feature_flags:read"
    FEATURE_FLAGS_UPDATE = "feature_flags:update"
    FEATURE_FLAGS_DELETE = "feature_flags:delete"


PERMISSION_DESCRIPTIONS: Final[dict[str, str]] = {
    Permission.ALL: "All permissions (superadmin only)",
    
    # Tenant permissions
    Permission.TENANT_READ: "View tenant information",
    Permission.TENANT_UPDATE: "Update tenant settings",
    Permission.TENANT_DELETE: "Delete tenant",
    Permission.TENANT_ALL: "All tenant management permissions",
    
    # User permissions
    Permission.USERS_CREATE: "Create new users",
    Permission.USERS_READ: "View all users in tenant",
    Permission.USERS_UPDATE: "Update user information",
    Permission.USERS_DELETE: "Delete users",
    Permission.USERS_READ_OWN: "View own user profile",
    Permission.USERS_ALL: "All user management permissions",
    
    # Role permissions
    Permission.ROLES_CREATE: "Create custom roles",
    Permission.ROLES_READ: "View roles",
    Permission.ROLES_UPDATE: "Update custom roles",
    Permission.ROLES_DELETE: "Delete custom roles",
    Permission.ROLES_ALL: "All role management permissions",
    
    # Policy permissions
    Permission.POLICIES_CREATE: "Create policies",
    Permission.POLICIES_READ: "View policies",
    Permission.POLICIES_UPDATE: "Update policies",
    Permission.POLICIES_DELETE: "Delete policies",
    Permission.POLICIES_ALL: "All policy management permissions",
    
    # Profile permissions
    Permission.PROFILE_UPDATE_OWN: "Update own profile",
    Permission.PROFILE_READ_OWN: "View own profile",
    
    # Audit permissions
    Permission.AUDIT_READ: "View all audit logs",
    Permission.AUDIT_READ_OWN: "View own audit logs",
    
    # Feature flag permissions
    Permission.FEATURE_FLAGS_CREATE: "Create feature flags",
    Permission.FEATURE_FLAGS_READ: "View feature flags",
    Permission.FEATURE_FLAGS_UPDATE: "Update feature flags",
    Permission.FEATURE_FLAGS_DELETE: "Delete feature flags",
}


# System role permission sets (for reference)
SYSTEM_ROLE_PERMISSIONS: Final[dict[str, list[str]]] = {
    "superadmin": [Permission.ALL],
    "tenant_admin": [
        Permission.TENANT_ALL,
        Permission.USERS_ALL,
        Permission.ROLES_CREATE,
        Permission.ROLES_UPDATE,
        Permission.ROLES_DELETE,
        Permission.POLICIES_ALL,
    ],
    "user": [
        Permission.USERS_READ_OWN,
        Permission.PROFILE_UPDATE_OWN,
        Permission.PROFILE_READ_OWN,
        Permission.AUDIT_READ_OWN,
    ],
}


def has_permission(user_permissions: list[str], required_permission: str) -> bool:
    """Check if user has the required permission.
    
    Args:
        user_permissions: List of permissions granted to user
        required_permission: Permission to check
    
    Returns:
        True if user has permission, False otherwise
    
    Examples:
        >>> has_permission(["*"], "users:create")
        True
        >>> has_permission(["users:*"], "users:create")
        True
        >>> has_permission(["users:read"], "users:create")
        False
    """
    # Wildcard permission grants everything
    if Permission.ALL in user_permissions:
        return True
    
    # Exact match
    if required_permission in user_permissions:
        return True
    
    # Check namespace wildcard (e.g., "users:*" grants "users:create")
    namespace = required_permission.split(":")[0]
    namespace_wildcard = f"{namespace}:*"
    if namespace_wildcard in user_permissions:
        return True
    
    return False


def validate_permissions(permissions: list[str]) -> tuple[bool, list[str]]:
    """Validate permission list format.
    
    Args:
        permissions: List of permission strings to validate
    
    Returns:
        Tuple of (is_valid, error_messages)
    
    Examples:
        >>> validate_permissions(["users:create", "users:read"])
        (True, [])
        >>> validate_permissions(["invalid_format", "users:create"])
        (False, ["Invalid permission format: 'invalid_format'"])
    """
    errors = []
    valid_permissions = {p.value for p in Permission}
    
    for perm in permissions:
        # Check if it's a known permission
        if perm in valid_permissions:
            continue
        
        # Check if it's a valid wildcard pattern (namespace:*)
        if ":" in perm and perm.endswith(":*"):
            namespace = perm.split(":")[0]
            # Verify namespace exists
            if any(p.startswith(f"{namespace}:") for p in valid_permissions):
                continue
        
        errors.append(f"Invalid permission format: '{perm}'")
    
    return (len(errors) == 0, errors)
