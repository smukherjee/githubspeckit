from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from domain.users.models import UserRepository, User, UserStatus


class UserLifecycleService:
    def __init__(self, repo: Optional[UserRepository] = None, audit_service=None, metrics_adapter=None):
        self._repo = repo or UserRepository()
        self._audit = audit_service
        # optional PromClientAdapter-compatible adapter
        self._metrics = metrics_adapter

    def disable(self, user_id: str, actor: str) -> User:
        u = self._repo.get(user_id)
        if not u:
            raise KeyError("user_not_found")
        u.status = UserStatus.disabled
        u.updated_by = actor
        u.updated_at = datetime.now(timezone.utc)
        self._repo.upsert(u)
        if self._audit:
            try:
                self._audit.emit(actor=actor, action="user.disable", target={"user_id": user_id, "tenant_id": getattr(u, "tenant_id", None)})
            except Exception:
                pass
        # decrement active_users gauge for tenant
        try:
            if self._metrics and getattr(u, "tenant_id", None):
                self._metrics.gauge_dec("active_users", tenant_id=getattr(u, "tenant_id", None), amount=1)
        except Exception:
            pass
        return u

    def restore(self, user_id: str, actor: str) -> User:
        u = self._repo.get(user_id)
        if not u:
            raise KeyError("user_not_found")
        if u.status != UserStatus.disabled:
            raise ValueError("user_not_disabled")
        u.status = UserStatus.active
        u.updated_by = actor
        u.updated_at = datetime.now(timezone.utc)
        self._repo.upsert(u)
        if self._audit:
            try:
                self._audit.emit(actor=actor, action="user.restore", target={"user_id": user_id, "tenant_id": getattr(u, "tenant_id", None)})
            except Exception:
                pass
        # increment active_users gauge for tenant
        try:
            if self._metrics and getattr(u, "tenant_id", None):
                self._metrics.gauge_inc("active_users", tenant_id=getattr(u, "tenant_id", None), amount=1)
        except Exception:
            pass
        return u


__all__ = ["UserLifecycleService"]
