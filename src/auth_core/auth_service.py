"""AuthenticationService orchestrates provider + hashing + MFA (FR-007, FR-008 subset).

Scope (Phase 2 increment):
- Authenticate with password provider.
- Perform hash upgrade if needed (returns flag to caller).
- Enforce MFA branch: if user has MFA enrolled but no code supplied raise MFACodeRequiredError.

Not implemented yet: actual MFA code verification, refresh tokens, audit hooks.
"""
from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime, timezone

from .registry import AuthProviderRegistry
from .hashers import Argon2PasswordHasher, default_hasher
from .mfa import MFARepository, MFACodeRequiredError
from .providers.base import AuthError, AuthResult

__all__ = ["AuthenticationService"]


class AuthenticationService:
    def __init__(
        self,
        *,
        registry: AuthProviderRegistry,
        hasher: Argon2PasswordHasher = default_hasher,
        mfa_repo: Optional[MFARepository] = None,
    ) -> None:
        self.registry = registry
        self.hasher = hasher
        self.mfa_repo = mfa_repo or MFARepository()

    async def login_password(
        self,
        *,
        user_id: str,
        stored_hash: str,
        password: str,
        mfa_code: Optional[str] = None,
        user_has_mfa: Optional[bool] = None,
    ) -> Dict[str, Any]:
        provider = self.registry.get("password")
        try:
            result: AuthResult = await provider.authenticate(username=user_id, password=password, stored_hash=stored_hash)
        except AuthError as e:  # bubble stable code
            raise e

        # Determine MFA requirement
        has_mfa = user_has_mfa if user_has_mfa is not None else self.mfa_repo.has_mfa(user_id)
        if has_mfa and not mfa_code:
            raise MFACodeRequiredError("mfa_required")
        # TODO: verify mfa_code when implemented

        upgrade = False
        if self.hasher.needs_rehash(stored_hash):
            # Caller will persist new hash
            upgrade = True
        return {
            "user_id": result.user_id,
            "needs_rehash": upgrade,
            "login_at": datetime.now(timezone.utc),
        }
