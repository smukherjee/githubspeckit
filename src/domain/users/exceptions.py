"""
Domain exceptions for user-related business logic errors.

These exceptions represent domain-level validation failures and business rule
violations. They should be raised by domain services and caught by adapters
(API routes) to be translated into appropriate HTTP responses.
"""


class UserDomainError(Exception):
    """Base exception for all user domain errors."""
    
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class DuplicateEmailError(UserDomainError):
    """
    Raised when attempting to create a user with an email that already exists
    within the same tenant (V1.0 per-tenant email uniqueness - FR-116).
    
    Example:
        raise DuplicateEmailError(
            email="user@example.com",
            tenant_id="tenant-123"
        )
    """
    
    def __init__(self, email: str, tenant_id: str):
        super().__init__(
            code="DUPLICATE_EMAIL",
            message=f"Email '{email}' already exists in tenant '{tenant_id}'"
        )
        self.email = email
        self.tenant_id = tenant_id


class UserNotFoundError(UserDomainError):
    """Raised when a user cannot be found by ID or email."""
    
    def __init__(self, identifier: str):
        super().__init__(
            code="USER_NOT_FOUND",
            message=f"User not found: {identifier}"
        )
        self.identifier = identifier


class InvalidUserStatusError(UserDomainError):
    """Raised when attempting an invalid user status transition."""
    
    def __init__(self, current_status: str, attempted_status: str):
        super().__init__(
            code="INVALID_STATUS_TRANSITION",
            message=f"Cannot transition from {current_status} to {attempted_status}"
        )
        self.current_status = current_status
        self.attempted_status = attempted_status
