import pytest
from domain.policy.evaluator import PolicyEvaluator, Policy, Decision, EvalResult

# TEST-POL-01 Policy evaluation ALLOW/DENY/ABSTAIN semantics basic (FR-012)


def test_policy_allows_matching_condition():
    allow_policy = Policy(policy_id="p1", version=1, resource_type="document", effect=Decision.ALLOW, condition=lambda ctx: ctx.get("role") == "reader")
    evaluator = PolicyEvaluator(policies=[allow_policy])
    res = evaluator.evaluate("document", {"role": "reader"})
    assert res.decision == Decision.ALLOW
    assert res.reason.startswith("policy:p1")


def test_policy_denies_matching_condition():
    deny_policy = Policy(policy_id="p2", version=1, resource_type="document", effect=Decision.DENY, condition=lambda ctx: ctx.get("role") == "banned")
    evaluator = PolicyEvaluator(policies=[deny_policy])
    res = evaluator.evaluate("document", {"role": "banned"})
    assert res.decision == Decision.DENY
    assert res.reason.startswith("policy:p2")


def test_policy_abstains_when_no_match():
    evaluator = PolicyEvaluator(policies=[])
    res = evaluator.evaluate("document", {"role": "unknown"})
    assert res.decision == Decision.ABSTAIN


def test_policy_version_ordering():
    # Newer policy overrides older one when its condition matches
    old = Policy(policy_id="p_old", version=1, resource_type="document", effect=Decision.ALLOW, condition=lambda ctx: True)
    new = Policy(policy_id="p_new", version=2, resource_type="document", effect=Decision.DENY, condition=lambda ctx: True)
    evaluator = PolicyEvaluator(policies=[old, new])
    res = evaluator.evaluate("document", {})
    assert res.decision == Decision.DENY
    assert "p_new" in res.reason
