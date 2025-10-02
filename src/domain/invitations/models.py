from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional

class InvitationStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    expired = "expired"
    revoked = "revoked"

@dataclass
class Invitation:
    invitation_id: str
    tenant_id: str
    email: str
    expires_at: datetime
    status: InvitationStatus = InvitationStatus.pending
    accepted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return now >= self.expires_at

class InvitationRepository:
    def __init__(self) -> None:
        self._store: dict[str, Invitation] = {}

    def upsert(self, invitation: Invitation) -> Invitation:
        self._store[invitation.invitation_id] = invitation
        return invitation

    def get(self, invitation_id: str) -> Optional[Invitation]:
        inv = self._store.get(invitation_id)
        if inv and inv.status == InvitationStatus.pending and inv.is_expired():
            inv.status = InvitationStatus.expired
        return inv

    def list_by_tenant(self, tenant_id: str) -> list[Invitation]:
        result = []
        for inv in self._store.values():
            if inv.tenant_id == tenant_id:
                if inv.status == InvitationStatus.pending and inv.is_expired():
                    inv.status = InvitationStatus.expired
                result.append(inv)
        return result
