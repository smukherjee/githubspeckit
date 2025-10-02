import pytest
from domain.policy.evaluator import PolicyEvaluator, Policy, Decision

class DummyMetrics:
    def __init__(self):
        self.observed = []
        self.counters = {}
    def histogram_observe(self, name, value, tenant_id=None, buckets=None):
        self.observed.append((name, value, tenant_id))
    def counter_inc(self, name, tenant_id=None, amount=1):
        self.counters[name] = self.counters.get(name, 0) + amount

def test_policy_evaluation_latency_histogram_name_and_observation():
    metrics = DummyMetrics()
    evaluator = PolicyEvaluator(metrics_adapter=metrics)
    # register trivial policy to force evaluation path
    evaluator.register(Policy(policy_id="p1", version=1, resource_type="res", condition=lambda c: True, effect=Decision.ALLOW))
    res = evaluator.evaluate("res", {"roles": [], "tenant_id": "t1"})
    assert res.decision == Decision.ALLOW
    names = {rec[0] for rec in metrics.observed}
    assert "policy_evaluation_latency_seconds" in names, "Expected canonical latency histogram observation"
    assert metrics.counters.get("policy_evaluations_total") == 1
