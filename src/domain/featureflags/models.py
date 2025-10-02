from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime, timezone

class FlagState(str, Enum):
    enabled = "enabled"
    disabled = "disabled"

@dataclass
class FeatureFlag:
    flag_id: str
    tenant_id: str
    key: str
    state: FlagState = FlagState.disabled
    variant: Optional[str] = None
    rules: Optional[Dict[str, Any]] = None  # Potential targeting logic, deferred
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

class FeatureFlagRepository:
    def __init__(self) -> None:
        self._store: dict[str, FeatureFlag] = {}

    def upsert(self, flag: FeatureFlag) -> FeatureFlag:
        self._store[flag.flag_id] = flag
        return flag

    def get(self, flag_id: str) -> Optional[FeatureFlag]:
        return self._store.get(flag_id)

    def list_by_tenant(self, tenant_id: str) -> list[FeatureFlag]:
        return [f for f in self._store.values() if f.tenant_id == tenant_id]
