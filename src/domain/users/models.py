from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List

class UserStatus(str, Enum):
    invited = "invited"
    active = "active"
    disabled = "disabled"

@dataclass
class User:
    user_id: str
    tenant_id: str
    email: str
    status: UserStatus = UserStatus.invited
    roles: List[str] = field(default_factory=list)
    password_hash: Optional[str] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

class UserRepository:
    def __init__(self) -> None:
        self._store: dict[str, User] = {}

    def upsert(self, user: User) -> User:
        self._store[user.user_id] = user
        return user

    def get(self, user_id: str) -> Optional[User]:
        return self._store.get(user_id)

    def list_by_tenant(self, tenant_id: str) -> list[User]:
        return [u for u in self._store.values() if u.tenant_id == tenant_id]

    def soft_delete(self, user_id: str) -> None:
        u = self._store[user_id]
        u.status = UserStatus.disabled
        u.updated_at = datetime.now(timezone.utc)

    def restore(self, user_id: str) -> None:
        u = self._store[user_id]
        if u.status == UserStatus.disabled:
            u.status = UserStatus.active
            u.updated_at = datetime.now(timezone.utc)
