"""Explicit replay detection store (IMPL-SEC-20 placeholder)."""
from __future__ import annotations
from time import time

class InMemoryReplayStore:
    def __init__(self):
        self._entries = {}

    def register(self, jti: str, ttl_seconds: int) -> bool:
        """Register a token JTI; returns False if replay detected (already present and not expired)."""
        now = time()
        exp, _ = self._entries.get(jti, (0, 0))
        if exp > now:
            return False
        self._entries[jti] = (now + ttl_seconds, now)
        return True

__all__ = ["InMemoryReplayStore"]
