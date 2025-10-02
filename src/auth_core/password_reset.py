"""Password reset service skeleton (FR-060..FR-065, C-008).

In-memory single-use token hash store. Real email dispatch omitted.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import hashlib
import uuid

__all__ = ["PasswordResetService", "PasswordResetError"]


class PasswordResetError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass
class _ResetEntry:
    user_id: str
    token_hash: str
    expires_at: datetime
    consumed: bool = False


class PasswordResetService:
    def __init__(self, default_exp_minutes: int = 30) -> None:
        self.default_exp_minutes = default_exp_minutes
        self._store: Dict[str, _ResetEntry] = {}  # token_hash -> entry

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def initiate(self, user_id: str, now: Optional[datetime] = None) -> str:
        now = now or datetime.now(timezone.utc)
        raw_token = uuid.uuid4().hex
        token_hash = self._hash(raw_token)
        entry = _ResetEntry(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=now + timedelta(minutes=self.default_exp_minutes),
        )
        self._store[token_hash] = entry
        return raw_token  # caller must deliver out-of-band

    def complete(self, token: str, now: Optional[datetime] = None) -> str:
        now = now or datetime.now(timezone.utc)
        token_hash = self._hash(token)
        entry = self._store.get(token_hash)
        if not entry:
            raise PasswordResetError("invalid_token")
        if entry.consumed:
            raise PasswordResetError("invalid_token")
        if now >= entry.expires_at:
            raise PasswordResetError("invalid_token")
        entry.consumed = True
        return entry.user_id
