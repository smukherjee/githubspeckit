"""Argon2id password hashing & verification utilities (FR-049, FR-051, C-023).

This module intentionally keeps no external framework dependencies so that the
auth_core package remains reusable. Parameter upgrade logic is exposed via
`needs_rehash` enabling transparent hash migration during authentication.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from argon2 import PasswordHasher, exceptions as argon_exc


@dataclass(slots=True)
class Argon2Params:
    time_cost: int = 3
    memory_cost: int = 64 * 1024  # kib
    parallelism: int = 2
    hash_len: int = 32
    salt_len: int = 16


class Argon2PasswordHasher:
    def __init__(self, params: Optional[Argon2Params] = None) -> None:
        self.params = params or Argon2Params()
        self._hasher = PasswordHasher(
            time_cost=self.params.time_cost,
            memory_cost=self.params.memory_cost,
            parallelism=self.params.parallelism,
            hash_len=self.params.hash_len,
            salt_len=self.params.salt_len,
        )

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, hashed: str, password: str) -> bool:
        try:
            return self._hasher.verify(hashed, password)
        except argon_exc.VerifyMismatchError:
            return False
        except argon_exc.VerificationError:
            return False

    def needs_rehash(self, hashed: str) -> bool:
        return self._hasher.check_needs_rehash(hashed)


default_hasher = Argon2PasswordHasher()
