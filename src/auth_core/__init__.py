"""auth_core package

Phase 2 delivers only a password-based authentication provider. The provider
architecture (registry + provider interface) allows future OIDC / SSO / MFA
providers to register themselves without modifying existing core code.

See Clarification C-024.
"""

from .registry import AuthProviderRegistry, default_registry  # noqa: F401
from .providers.base import AuthProvider, AuthResult, AuthError  # noqa: F401

__all__ = [
    "AuthProviderRegistry",
    "default_registry",
    "AuthProvider",
    "AuthResult",
    "AuthError",
]
