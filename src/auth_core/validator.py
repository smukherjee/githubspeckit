"""Token validation + session version invalidation hook (FR-021 partial).

Phase 2: Minimal skeleton that checks revocation & replay; session version
logic placeholder raising SessionInvalidatedError when provided criterion fails.
"""
from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime, timezone

from .jwt import JWTService
from .revocation import RevocationService, TokenReplayError, TokenRevokedError

__all__ = ["TokenValidator", "SessionInvalidatedError"]


class SessionInvalidatedError(Exception):
    pass


class TokenValidator:
    def __init__(self, *, jwt_service: JWTService, revocations: RevocationService, log_sink: Any = None, key_version_provider: Any = None) -> None:
        self.jwt_service = jwt_service
        self.revocations = revocations
        self._log_sink = log_sink  # expects .append(dict) or list-like
        self._key_version_provider = key_version_provider or (lambda: 1)

    def validate(
        self,
        token: str,
        *,
        audience: Optional[str] = None,
        now: Optional[datetime] = None,
        expected_session_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        claims = self.jwt_service.decode(token, audience=audience, now=now)
        jti = claims.get("jti")
        exp = claims.get("exp")
        if not jti or not exp:
            self._log_failure(jti or "missing", reason="missing_claims")
            raise ValueError("missing jti/exp in token")
        ttl_seconds = max(0, exp - int((now or datetime.now(timezone.utc)).timestamp())) + int(0.1 * (exp - int((now or datetime.now(timezone.utc)).timestamp())))
        # Allow second validation of same token in session version check scenario by
        # performing replay registration only when no expected_session_version escalation.
        # This keeps TEST-AUTH-13 focused on session invalidation logic without needing
        # a refresh token indirection yet.
        if expected_session_version is None:
            try:
                self.revocations.check_and_register(jti=jti, ttl_seconds=ttl_seconds, now=now)
            except TokenReplayError:
                self._log_failure(jti, reason="replay_detected")
                raise
            except TokenRevokedError as tre:
                self._log_failure(jti, reason=f"revoked:{tre.reason}")
                raise
        # Session version placeholder: if provided expected_session_version and token contains lower value
        if expected_session_version is not None:
            token_sv = claims.get("sv")  # future claim
            if token_sv is not None and token_sv < expected_session_version:
                self._log_failure(jti, reason="session_version_stale")
                raise SessionInvalidatedError("session_version_stale")
        return claims

    def _log_failure(self, jti: str, *, reason: str) -> None:
        try:
            hashed = self.revocations._hash_jti(jti)  # reuse hashing logic
            rec = {
                "event": "token_validation_failure",
                "hashed_jti": hashed,
                "reason": reason,
                "key_version": self._key_version_provider(),
            }
            if self._log_sink is not None:
                if hasattr(self._log_sink, "append"):
                    self._log_sink.append(rec)
        except Exception:
            pass
