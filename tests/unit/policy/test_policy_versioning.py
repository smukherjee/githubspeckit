import pytest
from domain.policy.evaluator import PolicyEvaluator, Policy, Decision

# TEST-POL-03 Policy version rollback scenario (FR-030)


def test_policy_version_rollback_selects_specific_version():
    v1 = Policy(policy_id="pA", version=1, resource_type="doc", effect=Decision.ALLOW, condition=lambda ctx: True)
    v2 = Policy(policy_id="pB", version=2, resource_type="doc", effect=Decision.DENY, condition=lambda ctx: True)
    ev = PolicyEvaluator(policies=[v1, v2])
    # default newest (v2) -> DENY
    res_newest = ev.evaluate("doc", {})
    assert res_newest.decision == Decision.DENY and "pB" in res_newest.reason
    # rollback to v1
    ev.set_active_version("doc", 1)
    res_rollback = ev.evaluate("doc", {})
    assert res_rollback.decision == Decision.ALLOW and "pA" in res_rollback.reason
