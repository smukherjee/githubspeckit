"""Role hierarchy endpoint for RBAC transparency.

Provides read-only access to available roles and their hierarchy.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from adapters.api.auth_deps import CurrentUser, get_current_user


router = APIRouter(prefix="/v1", tags=["roles"])


class RoleHierarchyResponse(BaseModel):
    """Response schema for role hierarchy."""
    name: str
    hierarchy_level: int
    description: str
    can_assign: list[str]
    permissions: list[str]


class RolesListResponse(BaseModel):
    """Response schema for role listing."""
    roles: list[RoleHierarchyResponse]
    total: int


# Role hierarchy definition (FR-089)
ROLE_HIERARCHY = [
    {
        "name": "superadmin",
        "hierarchy_level": 0,
        "description": "Global administrator with cross-tenant access",
        "can_assign": [],  # Cannot be assigned via API
        "permissions": [
            "tenant.create",
            "tenant.read_all",
            "tenant.update_all",
            "tenant.delete_all",
            "user.create_all",
            "user.read_all",
            "user.update_all",
            "user.delete_all",
            "policy.manage_all",
            "flag.manage_all",
            "audit.read_all"
        ]
    },
    {
        "name": "tenant_admin",
        "hierarchy_level": 1,
        "description": "Tenant-scoped administrator with full tenant permissions",
        "can_assign": ["developer", "analyst", "user", "service_account", "support_readonly"],
        "permissions": [
            "user.create_tenant",
            "user.read_tenant",
            "user.update_tenant",
            "user.delete_tenant",
            "policy.manage_tenant",
            "flag.manage_tenant",
            "audit.read_tenant"
        ]
    },
    {
        "name": "developer",
        "hierarchy_level": 2,
        "description": "Developer with feature flag and deployment permissions",
        "can_assign": [],
        "permissions": [
            "user.read_tenant",
            "flag.manage_tenant",
            "policy.read_tenant"
        ]
    },
    {
        "name": "analyst",
        "hierarchy_level": 2,
        "description": "Read-only access to audit logs and reports",
        "can_assign": [],
        "permissions": [
            "user.read_tenant",
            "audit.read_tenant",
            "policy.read_tenant"
        ]
    },
    {
        "name": "user",
        "hierarchy_level": 3,
        "description": "Standard application user",
        "can_assign": [],
        "permissions": [
            "user.read_self",
            "user.update_self",
            "audit.read_self"
        ]
    },
    {
        "name": "service_account",
        "hierarchy_level": 3,
        "description": "API access for automation and integrations",
        "can_assign": [],
        "permissions": [
            "user.read_tenant",
            "flag.read_tenant",
            "policy.read_tenant"
        ]
    },
    {
        "name": "support_readonly",
        "hierarchy_level": 3,
        "description": "Read-only support access for troubleshooting",
        "can_assign": [],
        "permissions": [
            "user.read_tenant",
            "audit.read_tenant",
            "policy.read_tenant",
            "flag.read_tenant"
        ]
    }
]


@router.get("/roles", response_model=RolesListResponse)
async def list_roles(
    current_user: CurrentUser
) -> RolesListResponse:
    """List all available roles with hierarchy information (FR-089).
    
    **RBAC**: All authenticated users can view roles (read-only).
    
    **Response**: Roles sorted by hierarchy_level (superadmin first, user last).
    
    **Purpose**: Provides transparency into role structure for:
    - Admin UI role assignment dropdowns
    - Documentation generation
    - RBAC debugging
    - Role assignment validation
    """
    # Sort by hierarchy level (ascending: superadmin first)
    sorted_roles = sorted(ROLE_HIERARCHY, key=lambda r: r["hierarchy_level"])
    
    return RolesListResponse(
        roles=[RoleHierarchyResponse(**role) for role in sorted_roles],
        total=len(sorted_roles)
    )
