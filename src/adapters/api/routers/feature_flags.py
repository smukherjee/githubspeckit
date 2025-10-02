from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from uuid import uuid4
from domain.featureflags.models import FeatureFlag, FlagState, FeatureFlagRepository

router = APIRouter(prefix="/v1/feature-flags", tags=["feature-flags"])

_repo = FeatureFlagRepository()  # Phase 2 in-memory


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
def create_flag(payload: FeatureFlagCreate):
    flag = FeatureFlag(
        flag_id=payload.flag_id or str(uuid4()),
        tenant_id=payload.tenant_id,
        key=payload.key,
        state=payload.state,
        variant=payload.variant,
        created_by="system",
        updated_by="system",
    )
    _repo.upsert(flag)
    return FeatureFlagResponse(**{
        "flag_id": flag.flag_id,
        "tenant_id": flag.tenant_id,
        "key": flag.key,
        "state": flag.state,
        "variant": flag.variant,
    })


@router.get("", response_model=FeatureFlagList)
def list_flags(tenant_id: str):
    items = _repo.list_by_tenant(tenant_id)
    return FeatureFlagList(flags=[FeatureFlagResponse(flag_id=f.flag_id, tenant_id=f.tenant_id, key=f.key, state=f.state, variant=f.variant) for f in items])

__all__ = ["router"]