from domain.featureflags.models import FeatureFlag, FlagState, FeatureFlagRepository
from services.featureflag_service import FeatureFlagService


def test_feature_flag_enable_disable():
    repo = FeatureFlagRepository()
    svc = FeatureFlagService(repo)
    flag = FeatureFlag(flag_id="f1", tenant_id="t1", key="beta_feature", state=FlagState.disabled)
    svc.upsert_flag(flag)
    assert not svc.is_enabled("t1", "beta_feature")
    flag.state = FlagState.enabled
    svc.upsert_flag(flag)
    assert svc.is_enabled("t1", "beta_feature")
