from __future__ import annotations

from typing import Optional

from .base import AuthProvider, AuthResult, AuthError
from ..hashers import default_hasher


class PasswordAuthProvider(AuthProvider):
    """Simple password provider stub.

    Phase 2: Does NOT perform real hashing/verification yet. It only illustrates
    provider registration; authenticate will raise NotImplementedError so that
    test scope stays focused on registry behavior. A later task (TEST-AUTH-01 /
    IMPL-AUTH-02) will supply proper Argon2id hash & verify logic.
    """

    def __init__(self, *, realm: Optional[str] = None) -> None:
        self._realm = realm or "default"

    @property
    def name(self) -> str:  # unique key in registry
        return "password"

    async def authenticate(self, **credentials) -> AuthResult:
        """Authenticate via password.

        Expected credentials: username (or email), password, and stored_hash (retrieved by higher layer).
        Hash upgrade path: if `default_hasher.needs_rehash(stored_hash)` is True after successful verify,
        caller should persist a new hash produced by `default_hasher.hash(password)` (not done here to keep
        provider pure per design). We signal upgrade need via AuthError code? Instead we expose a boolean
        in result in future; for now higher layer can call needs_rehash again.
        """
        username = credentials.get("username") or credentials.get("email")
        password = credentials.get("password")
        stored_hash = credentials.get("stored_hash")
        if not username or not password or not stored_hash:
            raise AuthError("invalid_credentials", "Missing credential fields")
        if not default_hasher.verify(stored_hash, password):
            raise AuthError("invalid_credentials", "Invalid username or password")
        # Transparent upgrade is deferred to orchestrator.
        return AuthResult(user_id=username)  # user_id placeholder (higher layer maps to canonical id)
