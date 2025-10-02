import pytest


def test_log_export_bounds_and_truncation():
    from fastapi.testclient import TestClient
    from adapters.api.app import create_app

    app = create_app()
    client = TestClient(app)
    # generate > max_limit logs (middleware logs each request)
    for i in range(30):
        client.get("/v1/health")
    resp = client.get("/v1/logs/export", params={"limit": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["records"]) == 10
    assert data["truncated"] is True
    assert data["total_available"] >= 30


def test_regression_trigger():
    from observability.regression_detector import RegressionDetector
    rd = RegressionDetector(window_size=3, threshold_ms=100)
    # need 3 samples (window_size) before evaluation; provide sustained high values
    assert not rd.observe(150)
    assert not rd.observe(140)
    assert rd.observe(130) is True


def test_revocation_audit_emission():
    from services.audit_service import AuditService
    from auth_core.revocation import RevocationService
    audit = AuditService()
    rev = RevocationService(audit_service=audit)
    rev.revoke(jti="abc", ttl_seconds=60, reason="logout")
    events = audit.query()
    assert any(e["action"] == "token.revoke" for e in events)


def test_token_validation_failure_logging():
    from auth_core.validator import TokenValidator, SessionInvalidatedError
    from auth_core.jwt import JWTService, JWTKeySet
    from auth_core.revocation import RevocationService
    import time
    ks = JWTKeySet(active_kid="k1", keys={"k1": "secret"})
    jwt_svc = JWTService(keys=ks, issuer="issuer", audience="aud")
    rev = RevocationService()
    sink = []
    token = jwt_svc.issue(sub="u", tenant_id="t", roles=[], extra={})
    tv = TokenValidator(jwt_service=jwt_svc, revocations=rev, log_sink=sink)
    # first validation registers; second triggers replay -> failure log
    tv.validate(token)
    with pytest.raises(Exception):
        tv.validate(token)
    assert any(r.get("event") == "token_validation_failure" and r.get("reason") == "replay_detected" for r in sink)


def test_metrics_snapshot_and_policy_latency_histogram():
    from fastapi.testclient import TestClient
    from adapters.api.app import create_app
    from domain.policy.evaluator import PolicyEvaluator, Policy, Decision

    app = create_app()
    client = TestClient(app)
    # register policy and evaluate to produce latency sample
    p = Policy(policy_id="p1", version=1, resource_type="doc", condition=lambda ctx: True, effect=Decision.ALLOW)
    pe = PolicyEvaluator(policies=[p], metrics_adapter=app.state.prom)
    pe.evaluate("doc", {"tenant_id": "t-1"})
    # Perform multiple evaluations to ensure histogram buckets recorded
    for _ in range(3):
        pe.evaluate("doc", {"tenant_id": "t-1"})
    metrics_text = client.get("/metrics").text
    assert "policy_eval_latency_ms_bucket" in metrics_text
