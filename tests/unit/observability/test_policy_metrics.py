from adapters.observability.prometheus_client_adapter import PromClientAdapter
from domain.policy.evaluator import PolicyEvaluator, Policy, Decision


def test_policy_evaluator_emits_denial_metric():
    # create a policy that denies when context['block'] is True
    def cond(ctx):
        return bool(ctx.get("block"))

    p = Policy(policy_id="p1", version=1, resource_type="res", condition=cond, effect=Decision.DENY)
    prom = PromClientAdapter()
    pe = PolicyEvaluator(policies=[p], metrics_adapter=prom)

    res = pe.evaluate("res", {"block": True, "tenant_id": "t-1"})
    assert res.decision == Decision.DENY
    out = prom.generate_latest().decode("utf-8")
    assert "policy_denials_total" in out
    assert 'tenant_id="t-1"' in out
