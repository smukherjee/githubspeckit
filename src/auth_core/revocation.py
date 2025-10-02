"""Revocation & replay detection service (FR-028, C-020, C-027).

Phase 2 in-memory implementation only. Stores SHA-256 hash of jti with an
expiry. Provides replay detection and explicit revocation reasons.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import hashlib

__all__ = [
    "RevocationService",
    "TokenReplayError",
    "TokenRevokedError",
]


class TokenReplayError(Exception):
    pass


class TokenRevokedError(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class _Entry:
    reason: str
    expires_at: datetime


class RevocationService:
    def __init__(self) -> None:
        # hashed_jti -> _Entry
        self._store: Dict[str, _Entry] = {}

    @staticmethod
    def _hash_jti(jti: str) -> str:
        return hashlib.sha256(jti.encode("utf-8")).hexdigest()

    def revoke(self, *, jti: str, ttl_seconds: int, reason: str, now: Optional[datetime] = None) -> None:
        now = now or datetime.now(timezone.utc)
        h = self._hash_jti(jti)
        self._store[h] = _Entry(reason=reason, expires_at=now + timedelta(seconds=ttl_seconds))

    def check_and_register(self, *, jti: str, ttl_seconds: int, now: Optional[datetime] = None) -> None:
        """If first time seeing jti store it, else raise replay.

        This models a replay store separate from explicit revocation.
        """
        now = now or datetime.now(timezone.utc)
        h = self._hash_jti(jti)
        self._prune(now)
        if h in self._store:
            # If existing entry marked explicit revocation we raise TokenRevokedError
            entry = self._store[h]
            if entry.reason != "replay":
                raise TokenRevokedError(entry.reason)
            raise TokenReplayError("replay_detected")
        self._store[h] = _Entry(reason="replay", expires_at=now + timedelta(seconds=ttl_seconds))

    def assert_not_revoked(self, *, jti: str, now: Optional[datetime] = None) -> None:
        now = now or datetime.now(timezone.utc)
        h = self._hash_jti(jti)
        self._prune(now)
        if h in self._store and self._store[h].reason != "replay":
            raise TokenRevokedError(self._store[h].reason)

    def _prune(self, now: datetime) -> None:
        expired = [k for k, v in self._store.items() if now >= v.expires_at]
        for k in expired:
            self._store.pop(k, None)
