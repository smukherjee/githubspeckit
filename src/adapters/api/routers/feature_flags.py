from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from domain.featureflags.models import FeatureFlag, FlagState
from adapters.api.deps import get_db_session, get_audit_service, AuditService
from adapters.api.auth_deps import CurrentUser
from adapters.persistence.repositories import SQLAlchemyFeatureFlagRepository

router = APIRouter(prefix="/v1/feature-flags", tags=["feature-flags"])


class FeatureFlagCreate(BaseModel):
    flag_id: Optional[str] = None
    tenant_id: str
    key: str
    state: FlagState = FlagState.disabled
    variant: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)


class FeatureFlagResponse(BaseModel):
    flag_id: str
    tenant_id: str
    key: str
    state: FlagState
    variant: Optional[str] = None
    model_config = ConfigDict(use_enum_values=True)


class FeatureFlagList(BaseModel):
    flags: List[FeatureFlagResponse]
    model_config = ConfigDict(use_enum_values=True)


@router.post("", response_model=FeatureFlagResponse, status_code=201)
async def create_flag(
    payload: FeatureFlagCreate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    audit_service: AuditService = Depends(get_audit_service)
) -> FeatureFlagResponse:
    """Create feature flag (Phase 3: database-backed)."""
    # Ensure state is FlagState enum (handle string or enum input)
    state_value = payload.state if isinstance(payload.state, FlagState) else FlagState(str(payload.state))
    
    flag = FeatureFlag(
        flag_id=payload.flag_id or str(uuid4()),
        tenant_id=payload.tenant_id,
        key=payload.key,
        state=state_value,
        variant=payload.variant,
        created_by="system",
        updated_by="system",
    )
    flag_repo = SQLAlchemyFeatureFlagRepository(session)
    await flag_repo.upsert(flag)
    await session.commit()
    
    # Audit logging: Feature flag creation
    await audit_service.log(
        action_type="feature_flag.create",
        tenant_id=flag.tenant_id,
        metadata={
            "flag_id": flag.flag_id,
            "key": flag.key,
            "state": flag.state.value,
            "variant": flag.variant,
            "created_by": current_user.user_id
        }
    )
    
    return FeatureFlagResponse(
        flag_id=flag.flag_id,
        tenant_id=flag.tenant_id,
        key=flag.key,
        state=flag.state,
        variant=flag.variant,
    )


@router.get("", response_model=FeatureFlagList)
async def list_flags(
    tenant_id: str,
    session: AsyncSession = Depends(get_db_session),
    include_deleted: bool = False
) -> FeatureFlagList:
    """List feature flags by tenant (FR-086/FR-087: supports include_deleted parameter)."""
    flag_repo = SQLAlchemyFeatureFlagRepository(session)
    items = await flag_repo.list_by_tenant(tenant_id, include_deleted=include_deleted)
    return FeatureFlagList(flags=[FeatureFlagResponse(flag_id=f.flag_id, tenant_id=f.tenant_id, key=f.key, state=f.state, variant=f.variant) for f in items])

__all__ = ["router"]