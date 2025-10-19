"""
Tenant context domain model.

Constitutional Compliance:
- Principle I: No FastAPI/Starlette imports (pure Python)
- Principle III: Explicit tenant_id for all operations
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class TenantContext:
    """
    Immutable tenant context extracted from JWT and session.
    
    This is a pure domain model with no framework dependencies.
    Implements the value object pattern for tenant identity.
    """
    
    tenant_id: UUID
    user_id: UUID
    roles: tuple[str, ...]  # Immutable tuple
    is_superadmin: bool
    session_tenant_id: Optional[UUID] = None
    
    def __post_init__(self) -> None:
        """Validate invariants."""
        # Ensure roles is a tuple (immutable)
        if not isinstance(self.roles, tuple):
            object.__setattr__(self, 'roles', tuple(self.roles))
    
    @property
    def effective_tenant_id(self) -> UUID:
        """
        Return the tenant ID that should be used for authorization.
        
        For superadmins with an active session switch, use session_tenant_id.
        Otherwise, use the JWT tenant_id.
        
        Returns:
            UUID: The effective tenant ID for this context
        """
        if self.is_superadmin and self.session_tenant_id is not None:
            return self.session_tenant_id
        return self.tenant_id
    
    def can_access_tenant(self, requested_tenant_id: UUID) -> bool:
        """
        Check if this context can access the requested tenant.
        
        Superadmins can access any tenant.
        Standard users can only access their own tenant (effective_tenant_id).
        
        Args:
            requested_tenant_id: The tenant being accessed
            
        Returns:
            bool: True if access is allowed, False otherwise
        """
        if self.is_superadmin:
            return True
        return self.effective_tenant_id == requested_tenant_id
