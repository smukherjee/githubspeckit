"""Tenant CRUD router (TEST-API-07 / IMPL-API-08 / Phase 3).

Implements database-backed create (idempotent by name), list, soft delete, restore.
Idempotency rule: creating a tenant with an existing exact lowercase name returns the existing tenant.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status, Header, Depends
from pydantic import BaseModel, field_validator, ConfigDict
from uuid import uuid4, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from domain.tenants.models import Tenant, TenantStatus
from adapters.persistence.repositories import SQLAlchemyTenantRepository
from adapters.api.deps import get_db_session, get_audit_service, AuditService
from adapters.api.auth_deps import CurrentUser

router = APIRouter(prefix="/v1/tenants", tags=["tenants"])


class TenantCreateRequest(BaseModel):
    name: str
    config_version: int = 1
    tenant_id: Optional[str] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Tenant name cannot be empty")
        return v.strip()
    
    @field_validator('tenant_id')
    @classmethod
    def validate_tenant_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                UUID(v)
            except ValueError:
                raise ValueError("tenant_id must be a valid UUID")
        return v


class TenantResponse(BaseModel):
    tenant_id: str
    name: str
    status: str
    config_version: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    idempotent: Optional[bool] = None
    model_config = ConfigDict(use_enum_values=True)


class TenantListResponse(BaseModel):
    tenants: list[TenantResponse]


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    payload: TenantCreateRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    audit_service: AuditService = Depends(get_audit_service),
    x_actor_id: str | None = Header(default=None, alias="X-Actor-ID")
) -> TenantResponse:
    """Create tenant with duplicate detection (Phase 3 database-backed).
    
    RBAC: Only superadmins can create tenants (FR-019).
    """
    # RBAC enforcement: Only superadmin can create tenants
    if not current_user.is_superadmin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can create tenants"
        )
    
    tenant_repo = SQLAlchemyTenantRepository(session)
    
    # Check if tenant with this name already exists - return 409 Conflict
    existing = await tenant_repo.get_by_name(payload.name)
    if existing:
        raise HTTPException(status_code=409, detail="Tenant with this name already exists")
    
    # Use provided tenant_id or generate new one
    tid = payload.tenant_id or str(uuid4())
    t = Tenant(tenant_id=tid, name=payload.name, config_version=payload.config_version)
    # populate audit metadata
    t.created_by = x_actor_id or current_user.user_id
    t.updated_by = t.created_by
    await tenant_repo.upsert(t)
    await session.commit()
    
    # Audit logging: Tenant creation
    await audit_service.log(
        action_type="tenant.create",
        tenant_id=t.tenant_id,
        metadata={
            "tenant_id": t.tenant_id,
            "name": t.name,
            "config_version": t.config_version,
            "created_by": current_user.user_id
        }
    )
    
    return TenantResponse(
        tenant_id=t.tenant_id,
        name=t.name,
        status=t.status.value,
        config_version=t.config_version,
        created_at=t.created_at,
        updated_at=t.updated_at,
        idempotent=False,
    )


@router.get("", response_model=TenantListResponse)
async def list_tenants(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session)
) -> TenantListResponse:
    """List all tenants (Phase 3 database-backed)."""
    tenant_repo = SQLAlchemyTenantRepository(session)
    tenants = await tenant_repo.list()
    return TenantListResponse(tenants=[
        TenantResponse(
            tenant_id=t.tenant_id,
            name=t.name,
            status=t.status.value,
            config_version=t.config_version,
            created_at=t.created_at,
            updated_at=t.updated_at
        ) for t in tenants
    ])


@router.delete("/{tenant_id}", status_code=204)
async def soft_delete_tenant(
    tenant_id: str,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    audit_service: AuditService = Depends(get_audit_service)
) -> None:
    """Soft-delete a tenant (Phase 3 database-backed)."""
    tenant_repo = SQLAlchemyTenantRepository(session)
    t = await tenant_repo.get(tenant_id)
    if not t:
        raise HTTPException(status_code=404, detail="not_found")
    if t.status == TenantStatus.soft_deleted:
        # Already deleted, return 204
        return
    await tenant_repo.soft_delete(tenant_id)
    await session.commit()
    
    # Audit logging: Tenant soft delete
    await audit_service.log(
        action_type="tenant.disable",
        tenant_id=tenant_id,
        metadata={
            "tenant_id": tenant_id,
            "name": t.name,
            "disabled_by": current_user.user_id,
            "previous_status": t.status.value
        }
    )
    # 204 returns no content


@router.post("/{tenant_id}/restore", status_code=200)
async def restore_tenant(
    tenant_id: str,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    audit_service: AuditService = Depends(get_audit_service)
) -> dict[str, str]:
    """Restore a soft-deleted tenant (Phase 3 database-backed)."""
    tenant_repo = SQLAlchemyTenantRepository(session)
    t = await tenant_repo.get(tenant_id)
    if not t:
        raise HTTPException(status_code=404, detail="not_found")
    if t.status == TenantStatus.active:
        # Already active, return current status
        return {"tenant_id": t.tenant_id, "status": t.status.value}
    await tenant_repo.restore(tenant_id)
    await session.commit()
    t2 = await tenant_repo.get(tenant_id)
    if t2 is None:
        raise HTTPException(status_code=500, detail="tenant_missing")
    
    # Audit logging: Tenant restore
    await audit_service.log(
        action_type="tenant.restore",
        tenant_id=tenant_id,
        metadata={
            "tenant_id": tenant_id,
            "name": t.name,
            "restored_by": current_user.user_id,
            "previous_status": t.status.value
        }
    )
    
    return {"tenant_id": t2.tenant_id, "status": t2.status.value}


__all__ = ["router"]
