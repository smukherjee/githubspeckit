"""Role repository interface (FR-122)."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from .entities import Role


class RoleRepository(ABC):
    """Abstract repository for role persistence.
    
    Defines the interface for role data access operations.
    Implementations must handle tenant isolation and system role protection.
    """
    
    @abstractmethod
    async def get_by_id(self, role_id: UUID) -> Optional[Role]:
        """Get role by ID.
        
        Args:
            role_id: Role identifier
        
        Returns:
            Role if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_name(self, name: str, tenant_id: Optional[UUID] = None) -> Optional[Role]:
        """Get role by name within tenant scope.
        
        Args:
            name: Role name
            tenant_id: Tenant ID (None for system roles)
        
        Returns:
            Role if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def list_all(
        self,
        tenant_id: Optional[UUID] = None,
        include_system: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> list[Role]:
        """List all roles with optional filtering.
        
        Args:
            tenant_id: Filter by tenant ID (None = all tenants, for superadmin)
            include_system: Whether to include system roles in results
            limit: Maximum number of results
            offset: Offset for pagination
        
        Returns:
            List of roles matching criteria
        """
        pass
    
    @abstractmethod
    async def list_by_tenant(self, tenant_id: UUID, include_system: bool = True) -> list[Role]:
        """List all roles for a specific tenant.
        
        Args:
            tenant_id: Tenant identifier
            include_system: Whether to include system roles
        
        Returns:
            List of roles (system + tenant custom roles)
        """
        pass
    
    @abstractmethod
    async def create(self, role: Role) -> Role:
        """Create a new role.
        
        Args:
            role: Role entity to create
        
        Returns:
            Created role with generated ID
        
        Raises:
            DuplicateRoleNameError: If role name already exists in tenant
        """
        pass
    
    @abstractmethod
    async def update(self, role: Role) -> Role:
        """Update an existing role.
        
        Args:
            role: Role entity with updates
        
        Returns:
            Updated role
        
        Raises:
            RoleNotFoundError: If role doesn't exist
            SystemRoleImmutableError: If attempting to update system role
        """
        pass
    
    @abstractmethod
    async def delete(self, role_id: UUID) -> bool:
        """Delete a role.
        
        Args:
            role_id: Role identifier
        
        Returns:
            True if deleted, False if not found
        
        Raises:
            SystemRoleImmutableError: If attempting to delete system role
        """
        pass
    
    @abstractmethod
    async def assign_to_user(self, user_id: UUID, role_id: UUID, assigned_by: UUID) -> bool:
        """Assign role to user.
        
        Args:
            user_id: User identifier
            role_id: Role identifier
            assigned_by: User ID performing the assignment
        
        Returns:
            True if assignment created, False if already exists
        
        Raises:
            RoleNotFoundError: If role doesn't exist
        """
        pass
    
    @abstractmethod
    async def revoke_from_user(self, user_id: UUID, role_id: UUID) -> bool:
        """Revoke role from user.
        
        Args:
            user_id: User identifier
            role_id: Role identifier
        
        Returns:
            True if revoked, False if assignment didn't exist
        """
        pass
    
    @abstractmethod
    async def get_user_roles(self, user_id: UUID) -> list[Role]:
        """Get all roles assigned to a user.
        
        Args:
            user_id: User identifier
        
        Returns:
            List of roles assigned to user
        """
        pass
    
    @abstractmethod
    async def count_role_users(self, role_id: UUID) -> int:
        """Count number of users assigned to a role.
        
        Args:
            role_id: Role identifier
        
        Returns:
            Number of users with this role
        """
        pass
