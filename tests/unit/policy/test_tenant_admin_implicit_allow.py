import pytest
from domain.policy.evaluator import PolicyEvaluator, Policy, Decision

# TEST-POL-07 Tenant admin implicit allow (FR-066)


def test_tenant_admin_implicit_allow_without_explicit_policy():
    ev = PolicyEvaluator(policies=[], valid_roles=["tenant_admin", "standard"])  # empty policy set
    res = ev.evaluate("tenant_resource", {"roles": ["tenant_admin"]})
    assert res.decision == Decision.ALLOW
    assert res.reason == "implicit_tenant_admin_allow"


def test_tenant_admin_restricted_action_requires_policy():
    ev = PolicyEvaluator(policies=[], valid_roles=["tenant_admin", "standard"])  # no explicit policy
    res = ev.evaluate("tenant_resource", {"roles": ["tenant_admin"], "restricted_action": True})
    # With restricted_action flag, implicit allow should not trigger; no policies => ABSTAIN
    assert res.decision == Decision.ABSTAIN
