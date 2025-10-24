"""Role domain exceptions (FR-122)."""


class RoleDomainError(Exception):
    """Base exception for role domain errors."""
    
    def __init__(self, message: str, code: str = "ROLE_ERROR"):
        """Initialize role domain error.
        
        Args:
            message: Human-readable error message
            code: Machine-readable error code
        """
        self.message = message
        self.code = code
        super().__init__(message)


class RoleNotFoundError(RoleDomainError):
    """Raised when a role cannot be found."""
    
    def __init__(self, role_id: str):
        """Initialize role not found error.
        
        Args:
            role_id: ID of the role that was not found
        """
        super().__init__(
            message=f"Role with ID '{role_id}' not found",
            code="ROLE_NOT_FOUND"
        )
        self.role_id = role_id


class SystemRoleImmutableError(RoleDomainError):
    """Raised when attempting to modify a system role."""
    
    def __init__(self, role_name: str, operation: str = "modify"):
        """Initialize system role immutable error.
        
        Args:
            role_name: Name of the system role
            operation: Operation attempted (modify, delete, etc.)
        """
        super().__init__(
            message=f"Cannot {operation} system role '{role_name}'. System roles are immutable.",
            code="SYSTEM_ROLE_IMMUTABLE"
        )
        self.role_name = role_name
        self.operation = operation


class PrivilegeEscalationError(RoleDomainError):
    """Raised when attempting privilege escalation via role creation/assignment."""
    
    def __init__(self, message: str = "Privilege escalation attempt detected"):
        """Initialize privilege escalation error.
        
        Args:
            message: Specific error message describing the escalation attempt
        """
        super().__init__(
            message=message,
            code="PRIVILEGE_ESCALATION"
        )


class InvalidPermissionsError(RoleDomainError):
    """Raised when role permissions are invalid."""
    
    def __init__(self, errors: list[str]):
        """Initialize invalid permissions error.
        
        Args:
            errors: List of validation error messages
        """
        message = "Invalid permissions: " + "; ".join(errors)
        super().__init__(
            message=message,
            code="INVALID_PERMISSIONS"
        )
        self.validation_errors = errors


class DuplicateRoleNameError(RoleDomainError):
    """Raised when attempting to create a role with duplicate name in tenant."""
    
    def __init__(self, role_name: str, tenant_id: str | None = None):
        """Initialize duplicate role name error.
        
        Args:
            role_name: Name of the duplicate role
            tenant_id: Tenant ID where duplicate exists (None for system roles)
        """
        scope = f"tenant {tenant_id}" if tenant_id else "system roles"
        super().__init__(
            message=f"Role with name '{role_name}' already exists in {scope}",
            code="DUPLICATE_ROLE_NAME"
        )
        self.role_name = role_name
        self.tenant_id = tenant_id
