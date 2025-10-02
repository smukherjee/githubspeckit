from __future__ import annotations

from typing import Optional

from domain.featureflags.models import FeatureFlag, FeatureFlagRepository, FlagState


class FeatureFlagService:
    def __init__(self, repo: Optional[FeatureFlagRepository] = None):
        self._repo = repo or FeatureFlagRepository()

    def upsert_flag(self, flag: FeatureFlag) -> FeatureFlag:
        return self._repo.upsert(flag)

    def is_enabled(self, tenant_id: str, key: str) -> bool:
        flags = self._repo.list_by_tenant(tenant_id)
        for f in flags:
            if f.key == key:
                return f.state == FlagState.enabled
        return False


__all__ = ["FeatureFlagService"]
