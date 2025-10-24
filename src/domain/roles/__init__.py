"""Role domain package for RBAC implementation (FR-122)."""

from .entities import Role
from .exceptions import (
    RoleDomainError,
    RoleNotFoundError,
    SystemRoleImmutableError,
    PrivilegeEscalationError,
)
from .permissions import Permission, PERMISSION_DESCRIPTIONS
from .repositories import RoleRepository

__all__ = [
    "Role",
    "RoleDomainError",
    "RoleNotFoundError",
    "SystemRoleImmutableError",
    "PrivilegeEscalationError",
    "Permission",
    "PERMISSION_DESCRIPTIONS",
    "RoleRepository",
]
