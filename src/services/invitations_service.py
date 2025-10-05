from __future__ import annotations

from hashlib import sha256
from datetime import datetime, timezone
from typing import Any, Optional
import inspect

from domain.invitations.models import Invitation, InvitationRepository, InvitationStatus
from uuid import uuid4
from datetime import timedelta


class InvitationService:
    def __init__(self, repo: Optional[InvitationRepository] = None, audit_service: Any = None, metrics_adapter: Any = None) -> None:
        self._repo = repo or InvitationRepository()
        self._audit = audit_service
        self._metrics = metrics_adapter

    def initiate(self, invitation: Invitation) -> Invitation:
        # store invitation as-is
        return self._repo.upsert(invitation)

    async def create_invitation(self, *, tenant_id: str, email: str, actor: str, ttl_minutes: int = 60) -> Invitation:
        """Convenience factory used by early API tests prior to full contract exposure.

        Generates an invitation_id + expiry and persists it.
        Idempotency by (tenant_id,email) NOT enforced in this minimal phase.
        """
        invitation = Invitation(
            invitation_id=str(uuid4()),
            tenant_id=tenant_id,
            email=email,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
            created_by=actor,
            updated_by=actor,
        )
        result = self._repo.upsert(invitation)  # type: ignore[misc]
        if inspect.iscoroutine(result):
            return await result
        return result  # type: ignore[return-value]

    async def accept(self, invitation_id: str, actor: str) -> Invitation:
        result = self._repo.get(invitation_id)  # type: ignore[misc]
        inv = await result if inspect.iscoroutine(result) else result
        if not inv:
            # increment auth_failures_total for telemetry
            try:
                if self._metrics and getattr(inv, "tenant_id", None):
                    self._metrics.counter_inc("auth_failures_total", tenant_id=getattr(inv, "tenant_id", None), amount=1)
            except Exception:
                pass
            raise KeyError("invitation_not_found")
        # idempotent accept: if already accepted, return it
        if inv.status == InvitationStatus.accepted:
            # emit audit event for repeated accept attempts
            if self._audit:
                try:
                    self._audit.emit(actor=actor, action="invitation.accept.already", target={"invitation_id": invitation_id})
                except Exception:
                    pass
            return inv
        if inv.status != InvitationStatus.pending:
            raise ValueError("invitation_not_active")
        if inv.is_expired():
            inv.status = InvitationStatus.expired
            inv.updated_at = datetime.now(timezone.utc)
            result = self._repo.upsert(inv)  # type: ignore[misc]
            if inspect.iscoroutine(result):
                await result
            try:
                if self._metrics and getattr(inv, "tenant_id", None):
                    self._metrics.counter_inc("auth_failures_total", tenant_id=getattr(inv, "tenant_id", None), amount=1)
            except Exception:
                pass
            raise ValueError("invitation_expired")
        inv.status = InvitationStatus.accepted
        inv.accepted_at = datetime.now(timezone.utc)
        inv.updated_by = actor
        inv.updated_at = datetime.now(timezone.utc)
        result = self._repo.upsert(inv)  # type: ignore[misc]
        if inspect.iscoroutine(result):
            await result
        if self._audit:
            try:
                self._audit.emit(actor=actor, action="invitation.accept", target={"invitation_id": invitation_id, "tenant_id": getattr(inv, "tenant_id", None)})
            except Exception:
                pass
        return inv

    @staticmethod
    def invitation_token_hash(token: str) -> str:
        return sha256(token.encode("utf-8")).hexdigest()


__all__ = ["InvitationService"]
