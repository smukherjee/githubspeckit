"""auth_core package

Phase 2 delivers only a password-based authentication provider. The provider
architecture (registry + provider interface) allows future OIDC / SSO / MFA
providers to register themselves without modifying existing core code.

See Clarification C-024.
"""

from .registry import AuthProviderRegistry, default_registry  # noqa: F401
from .providers.base import AuthProvider, AuthResult, AuthError  # noqa: F401
from .jwt import JWTService, JWTKeySet  # noqa: F401
from .revocation import RevocationService, TokenReplayError, TokenRevokedError
from .mfa import MFARepository, MFACodeRequiredError
from .password_reset import PasswordResetService, PasswordResetError
from .auth_service import AuthenticationService
from .validator import TokenValidator, SessionInvalidatedError

__all__ = [
    "AuthProviderRegistry",
    "default_registry",
    "AuthProvider",
    "AuthResult",
    "AuthError",
    "JWTService",
    "JWTKeySet",
    # New Auth Core exports (rotation/revocation/MFA/reset/login lifecycle)
    "RevocationService",
    "TokenReplayError",
    "TokenRevokedError",
    "MFARepository",
    "MFACodeRequiredError",
    "PasswordResetService",
    "PasswordResetError",
    "AuthenticationService",
    "TokenValidator",
    "SessionInvalidatedError",
]
