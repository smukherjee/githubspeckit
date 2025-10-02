import pytest
from domain.policy.evaluator import PolicyEvaluator, Policy, Decision

# TEST-POL-05 Role enforcement & undefined role rejection (FR-019, FR-031, FR-067, FR-068)


def test_undefined_role_rejected():
    allow = Policy(policy_id="p1", version=1, resource_type="thing", effect=Decision.ALLOW, condition=lambda ctx: True)
    ev = PolicyEvaluator(policies=[allow], valid_roles=["reader", "writer"])
    res = ev.evaluate("thing", {"roles": ["evil"]})
    assert res.decision == Decision.DENY
    assert res.reason == "undefined_role"


def test_defined_roles_allow_evaluation():
    allow = Policy(policy_id="p1", version=1, resource_type="thing", effect=Decision.ALLOW, condition=lambda ctx: True)
    ev = PolicyEvaluator(policies=[allow], valid_roles=["reader", "writer"])
    res = ev.evaluate("thing", {"roles": ["reader"]})
    assert res.decision == Decision.ALLOW
