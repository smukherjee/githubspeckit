"""Bootstrap CLI (IMPL-API-26) implements deterministic seed (FR-069, TEST-API-25).

Creates a baseline tenant and an admin user with deterministic UUIDv5 values so repeated
invocations are idempotent (no duplicates). Uses in-memory repositories for Phase 2.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

from domain.tenants.models import Tenant, TenantRepository, TenantStatus
from domain.users.models import User, UserRepository, UserStatus

NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")  # stable namespace constant


@dataclass
class BootstrapResult:
    tenant_id: str
    admin_user_id: str
    created: bool
    summary: dict[str, object]


def deterministic_uuid(name: str) -> str:
    return str(uuid.uuid5(NAMESPACE, name))


def bootstrap(tenant_slug: str = "primary", admin_email: str = "admin@example.com") -> BootstrapResult:
    t_repo = TenantRepository()
    u_repo = UserRepository()
    tenant_id = deterministic_uuid(f"tenant:{tenant_slug}")
    user_id = deterministic_uuid(f"user:{admin_email.lower()}")
    existing_tenant = t_repo.get(tenant_id)
    created = False
    tenant_conflict = bool(existing_tenant)
    if not existing_tenant:
        tenant = Tenant(tenant_id=tenant_id, name=tenant_slug, status=TenantStatus.active, created_by=None, updated_by=None)
        t_repo.upsert(tenant)
        created = True
    existing_user = u_repo.get(user_id)
    user_conflict = bool(existing_user)
    if not existing_user:
        user = User(user_id=user_id, tenant_id=tenant_id, email=admin_email.lower(), status=UserStatus.active, roles=["tenant_admin"], created_by=None, updated_by=None)
        u_repo.upsert(user)
        created = True or created
    conflict_pairs = [("tenant_exists", tenant_conflict), ("admin_exists", user_conflict)]
    summary = {
        "tenant_id": tenant_id,
        "admin_user_id": user_id,
        "idempotent": tenant_conflict and user_conflict,
        "conflicts": [c for c, present in conflict_pairs if present],
        "counts": {"tenants": len(t_repo.list()), "users": len(u_repo.list_by_tenant(tenant_id))},
    }
    return BootstrapResult(tenant_id=tenant_id, admin_user_id=user_id, created=created, summary=summary)


def main():  # pragma: no cover - thin wrapper
    res = bootstrap()
    print({"tenant_id": res.tenant_id, "admin_user_id": res.admin_user_id, "created": res.created})


if __name__ == "__main__":  # pragma: no cover
    main()
