from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable, Optional


@dataclass(slots=True)
class AuthResult:
    """Represents a successful authentication outcome.

    In Phase 2 minimal shape only; future phases can extend with roles, claims,
    tenant context, etc. Keep small now to reduce churn.
    """

    user_id: str
    tenant_id: Optional[str] = None


class AuthError(Exception):
    """Raised when an authentication attempt fails.

    Future: add stable error codes (e.g. invalid_credentials, mfa_required).
    """

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


@runtime_checkable
class AuthProvider(Protocol):  # pragma: no cover - structural typing
    """Protocol all auth providers must implement.

    Providers should be pure wrt credential verification and MUST NOT have
    side effects (auditing, rate limiting) baked in; those belong in higher
    orchestration layers.
    """

    @property
    def name(self) -> str:  # unique registry key
        ...

    async def authenticate(self, **credentials) -> AuthResult:
        """Attempt authentication.

        Implementations should raise AuthError with stable `code` values.
        """
        ...
