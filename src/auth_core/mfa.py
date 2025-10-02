"""MFA repository placeholder (FR-061/FR-062, C-024 defers real factors).

Phase 2: Only supports a flag indicating whether a user has MFA enrolled.
"""
from __future__ import annotations
from typing import Dict

__all__ = ["MFARepository", "MFACodeRequiredError"]


class MFACodeRequiredError(Exception):
    pass


class MFARepository:
    def __init__(self) -> None:
        # user_id -> enrolled(bool)
        self._enrolled: Dict[str, bool] = {}

    def set_enrolled(self, user_id: str, enrolled: bool) -> None:
        self._enrolled[user_id] = enrolled

    def has_mfa(self, user_id: str) -> bool:
        return self._enrolled.get(user_id, False)
