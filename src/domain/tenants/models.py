from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

class TenantStatus(str, Enum):
    active = "active"
    soft_deleted = "soft_deleted"

@dataclass
class Tenant:
    tenant_id: str
    name: str
    status: TenantStatus = TenantStatus.active
    config_version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class TenantRepository:
    """In-memory repository interface placeholder.
    Real implementation will be async + persistence adapter.
    """
    def __init__(self) -> None:
        self._store: dict[str, Tenant] = {}

    def upsert(self, tenant: Tenant) -> Tenant:
        self._store[tenant.tenant_id] = tenant
        return tenant

    def get(self, tenant_id: str) -> Optional[Tenant]:
        return self._store.get(tenant_id)

    def list(self) -> list[Tenant]:
        return list(self._store.values())

    def soft_delete(self, tenant_id: str) -> None:
        t = self._store[tenant_id]
        t.status = TenantStatus.soft_deleted
        t.updated_at = datetime.now(timezone.utc)

    def restore(self, tenant_id: str) -> None:
        t = self._store[tenant_id]
        t.status = TenantStatus.active
        t.updated_at = datetime.now(timezone.utc)
