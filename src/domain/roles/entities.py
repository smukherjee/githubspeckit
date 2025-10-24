"""Role entity for RBAC system (FR-122)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from .exceptions import SystemRoleImmutableError, InvalidPermissionsError
from .permissions import validate_permissions, Permission


@dataclass
class Role:
    """Role entity representing RBAC role with permissions.
    
    Roles define sets of permissions that can be assigned to users.
    System roles (superadmin, tenant_admin, user) are immutable.
    Custom roles can be created by tenant admins below their hierarchy level.
    
    Attributes:
        id: Unique role identifier
        name: Role name (unique per tenant)
        tenant_id: Tenant ID (None for system roles)
        is_system: Whether this is an immutable system role
        permissions: List of permission strings
        description: Optional role description
        created_at: Creation timestamp
        updated_at: Last update timestamp
        created_by: User ID who created the role
        updated_by: User ID who last updated the role
    """
    
    name: str
    permissions: list[str]
    tenant_id: Optional[UUID] = None
    is_system: bool = False
    description: Optional[str] = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    
    def __post_init__(self):
        """Validate role after initialization."""
        # Validate permissions format
        is_valid, errors = validate_permissions(self.permissions)
        if not is_valid:
            raise InvalidPermissionsError(errors)
        
        # System roles must have null tenant_id
        if self.is_system and self.tenant_id is not None:
            raise ValueError("System roles must have null tenant_id")
        
        # Custom roles must have tenant_id
        if not self.is_system and self.tenant_id is None:
            raise ValueError("Custom roles must have a tenant_id")
    
    def update_permissions(self, new_permissions: list[str], updated_by: UUID) -> None:
        """Update role permissions.
        
        Args:
            new_permissions: New list of permission strings
            updated_by: User ID making the update
        
        Raises:
            SystemRoleImmutableError: If attempting to update system role
            InvalidPermissionsError: If permissions are invalid
        """
        if self.is_system:
            raise SystemRoleImmutableError(self.name, "update permissions of")
        
        # Validate new permissions
        is_valid, errors = validate_permissions(new_permissions)
        if not is_valid:
            raise InvalidPermissionsError(errors)
        
        self.permissions = new_permissions
        self.updated_at = datetime.utcnow()
        self.updated_by = updated_by
    
    def update_description(self, description: str, updated_by: UUID) -> None:
        """Update role description.
        
        Args:
            description: New role description
            updated_by: User ID making the update
        
        Raises:
            SystemRoleImmutableError: If attempting to update system role
        """
        if self.is_system:
            raise SystemRoleImmutableError(self.name, "update description of")
        
        self.description = description
        self.updated_at = datetime.utcnow()
        self.updated_by = updated_by
    
    def has_permission(self, permission: str) -> bool:
        """Check if role has a specific permission.
        
        Args:
            permission: Permission to check
        
        Returns:
            True if role has permission, False otherwise
        """
        from .permissions import has_permission
        return has_permission(self.permissions, permission)
    
    def has_all_permissions(self) -> bool:
        """Check if role has wildcard (*) permission.
        
        Returns:
            True if role has all permissions, False otherwise
        """
        return Permission.ALL in self.permissions
    
    def can_manage_role(self, other_role: "Role") -> bool:
        """Check if this role can manage another role.
        
        Args:
            other_role: Role to check management permissions for
        
        Returns:
            True if this role can manage the other role, False otherwise
        
        Rules:
            - System roles cannot be managed by anyone
            - Roles with * permission can manage any custom role
            - Roles with roles:* can manage custom roles in same tenant
            - Custom roles cannot manage other custom roles
        """
        # System roles are immutable
        if other_role.is_system:
            return False
        
        # Wildcard permission can manage anything
        if self.has_all_permissions():
            return True
        
        # roles:* permission can manage custom roles in same tenant
        if self.has_permission("roles:*") and self.tenant_id == other_role.tenant_id:
            return True
        
        return False
    
    def to_dict(self) -> dict:
        """Convert role to dictionary representation.
        
        Returns:
            Dictionary with role data
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "is_system": self.is_system,
            "permissions": self.permissions,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Role":
        """Create role from dictionary representation.
        
        Args:
            data: Dictionary with role data
        
        Returns:
            Role instance
        """
        return cls(
            id=UUID(data["id"]) if data.get("id") else uuid4(),
            name=data["name"],
            tenant_id=UUID(data["tenant_id"]) if data.get("tenant_id") else None,
            is_system=data.get("is_system", False),
            permissions=data["permissions"],
            description=data.get("description"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
            created_by=UUID(data["created_by"]) if data.get("created_by") else None,
            updated_by=UUID(data["updated_by"]) if data.get("updated_by") else None,
        )


# Fixed UUIDs for system roles (matching migration)
SYSTEM_ROLE_IDS = {
    "superadmin": UUID("00000000-0000-0000-0000-000000000001"),
    "tenant_admin": UUID("00000000-0000-0000-0000-000000000002"),
    "user": UUID("00000000-0000-0000-0000-000000000003"),
}
