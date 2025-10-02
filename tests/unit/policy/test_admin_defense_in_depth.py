import pytest
from domain.policy.evaluator import PolicyEvaluator, Policy, Decision
from domain.policy.admin_scope_validator import AdminScopeValidator, AdminScopeError

# TEST-POL-09: Admin defense-in-depth (FR-036, C-026)


def _validator(policy: Policy | None = None):
    evaluator = PolicyEvaluator(policies=[policy] if policy else [], valid_roles=["superadmin", "tenant_admin", "standard"])
    return AdminScopeValidator(evaluator)


def test_missing_principal_layer():
    v = _validator()
    with pytest.raises(AdminScopeError) as exc:
        v.validate("admin.res", {"roles": ["superadmin"], "admin_scope_explicit": True})
    assert exc.value.code == "admin_scope_missing_layer"
    assert "principal" in exc.value.layers


def test_missing_admin_role_layer():
    v = _validator()
    with pytest.raises(AdminScopeError) as exc:
        v.validate("admin.res", {"principal": "u1", "roles": ["standard"], "admin_scope_explicit": True})
    assert exc.value.code == "admin_scope_missing_layer"
    assert "admin_role" in exc.value.layers


def test_missing_explicit_scope_layer():
    v = _validator()
    with pytest.raises(AdminScopeError) as exc:
        v.validate("admin.res", {"principal": "u1", "roles": ["superadmin"]})
    assert exc.value.code == "admin_scope_missing_layer"
    assert "explicit_scope" in exc.value.layers


def test_policy_denial_overrides():
    deny = Policy(policy_id="pdeny", version=1, resource_type="admin.res", effect=Decision.DENY, condition=lambda ctx: True)
    v = _validator(deny)
    with pytest.raises(AdminScopeError) as exc:
        v.validate("admin.res", {"principal": "u1", "roles": ["superadmin"], "admin_scope_explicit": True})
    assert exc.value.code == "admin_scope_policy_denied"
    assert exc.value.policy_reason.startswith("policy:pdeny")


def test_success_allow():
    allow = Policy(policy_id="pallow", version=1, resource_type="admin.res", effect=Decision.ALLOW, condition=lambda ctx: True)
    v = _validator(allow)
    res = v.validate("admin.res", {"principal": "u1", "roles": ["tenant_admin"], "admin_scope_explicit": True})
    assert res.decision == Decision.ALLOW
    assert set(res.satisfied_layers) == {"principal", "admin_role", "explicit_scope", "policy_eval"}


def test_success_abstain_no_policies():
    v = _validator()
    res = v.validate("admin.res", {"principal": "u1", "roles": ["superadmin"], "admin_scope_explicit": True})
    from domain.policy.evaluator import Decision as EvalDecision
    assert res.decision == EvalDecision.ABSTAIN

