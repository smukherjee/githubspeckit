"""Tenant CRUD router (TEST-API-07 / IMPL-API-08).

Implements in-memory create (idempotent by name), list, soft delete, restore.
Idempotency rule: creating a tenant with an existing exact lowercase name returns the existing tenant.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status, Header
from uuid import uuid4
from domain.tenants.models import Tenant, TenantRepository, TenantStatus

router = APIRouter(prefix="/v1/tenants", tags=["tenants"])

_repo = TenantRepository()
_name_index: dict[str, str] = {}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_tenant(payload: dict, x_actor_id: str | None = Header(default=None, alias="X-Actor-ID")):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name_required")
    key = name.lower()
    existing_id = _name_index.get(key)
    if existing_id:
        t = _repo.get(existing_id)
        if t is None:  # defensive (should not happen)
            raise HTTPException(status_code=500, detail="tenant_missing")
        return {
            "tenant_id": t.tenant_id,
            "name": t.name,
            "status": t.status.value,
            "idempotent": True,
        }
    tid = str(uuid4())
    t = Tenant(tenant_id=tid, name=name)
    # populate audit metadata
    t.created_by = x_actor_id or "system"
    t.updated_by = t.created_by
    _repo.upsert(t)
    _name_index[key] = tid
    return {
        "tenant_id": t.tenant_id,
        "name": t.name,
        "status": t.status.value,
        "idempotent": False,
        "created_by": t.created_by,
        "updated_by": t.updated_by,
    }


@router.get("")
async def list_tenants() -> dict[str, list[dict[str, str]]]:
    out = []
    for t in _repo.list():
        out.append({"tenant_id": t.tenant_id, "name": t.name, "status": t.status.value})
    return {"tenants": out}


@router.post("/{tenant_id}/delete")
async def soft_delete_tenant(tenant_id: str) -> dict[str, str]:
    t = _repo.get(tenant_id)
    if not t:
        raise HTTPException(status_code=404, detail="not_found")
    if t.status == TenantStatus.soft_deleted:
        return {"tenant_id": t.tenant_id, "status": t.status.value}
    _repo.soft_delete(tenant_id)
    t2 = _repo.get(tenant_id)
    if t2 is None:
        raise HTTPException(status_code=500, detail="tenant_missing")
    return {"tenant_id": t2.tenant_id, "status": t2.status.value}


@router.post("/{tenant_id}/restore")
async def restore_tenant(tenant_id: str) -> dict[str, str]:
    t = _repo.get(tenant_id)
    if not t:
        raise HTTPException(status_code=404, detail="not_found")
    if t.status == TenantStatus.active:
        return {"tenant_id": t.tenant_id, "status": t.status.value}
    _repo.restore(tenant_id)
    t2 = _repo.get(tenant_id)
    if t2 is None:
        raise HTTPException(status_code=500, detail="tenant_missing")
    return {"tenant_id": t2.tenant_id, "status": t2.status.value}


__all__ = ["router"]
