import pytest


def test_log_export_bounds_and_truncation():
    """Test log export with filtering, bounds, and redaction (FR-016, FR-072, FR-073).
    
    Note: Log export endpoint requires authentication (superadmin or tenant_admin role).
    """
    from fastapi.testclient import TestClient
    from adapters.api.app import create_app
    from auth_core.jwt import JWTService, JWTKeySet

    app = create_app()

    # Create authenticated client with superadmin token
    # Use the same JWT configuration as the app's get_jwt_service() in deps.py
    jwt_keys = JWTKeySet(active_kid="v1", keys={"v1": "dev-secret-key"})
    jwt_service = JWTService(keys=jwt_keys, issuer="modern-backend", audience="modern-backend")
    
    # Generate superadmin token (using valid UUID format for user_id)
    token = jwt_service.issue(
        sub="11111111-1111-1111-1111-111111111111",  # Superadmin user UUID
        tenant_id="00000000-0000-0000-0000-000000000000",  # Superadmin tenant UUID
        roles=["superadmin"],
        extra={}
    )
    
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Generate > limit logs (middleware logs each request)
    for i in range(30):
        client.get("/api/v1/health")
    
    # Test basic limit and truncation (with authentication)
    resp = client.get("/api/v1/logs/export", params={"limit": 10}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["records"]) == 10
    assert data["truncated"] is True
    assert data["total_available"] >= 30
    
    # Test category filter (with authentication)
    resp = client.get("/api/v1/logs/export", params={"category": "info", "limit": 5}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert all(r.get("level") == "info" for r in data["records"])
    
    # Test redaction - sensitive fields should be redacted (with authentication)
    resp = client.get("/api/v1/logs/export", params={"limit": 5}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    for record in data["records"]:
        # If authorization header was present, it should be redacted
        if "headers" in record and "authorization" in record["headers"]:
            assert record["headers"]["authorization"] == "REDACTED"


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
    """Test policy evaluation histogram is exposed (FR-032, FR-034, C-044).
    
    Note: Metrics endpoints now require authentication per V1.0 RBAC enforcement.
    """
    from fastapi.testclient import TestClient
    from adapters.api.app import create_app
    from domain.policy.evaluator import PolicyEvaluator, Policy, Decision
    from auth_core.jwt import JWTService, JWTKeySet

    app = create_app()

    # Create authenticated client with superadmin token
    # Use the same JWT configuration as the app's get_jwt_service() in deps.py
    jwt_keys = JWTKeySet(active_kid="v1", keys={"v1": "dev-secret-key"})
    jwt_service = JWTService(keys=jwt_keys, issuer="modern-backend", audience="modern-backend")
    
    token = jwt_service.issue(
        sub="11111111-1111-1111-1111-111111111111",  # Superadmin user UUID
        tenant_id="00000000-0000-0000-0000-000000000000",  # Superadmin tenant UUID
        roles=["superadmin"],
        extra={}
    )
    
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Register policy and evaluate to produce latency samples
    p = Policy(
        policy_id="p1",
        version=1,
        resource_type="doc",
        condition=lambda ctx: True,
        effect=Decision.ALLOW
    )
    pe = PolicyEvaluator(policies=[p], metrics_adapter=app.state.prom)
    
    # Perform multiple evaluations to ensure histogram buckets are recorded
    for _ in range(5):
        pe.evaluate("doc", {"tenant_id": "t-1"})
    
    # Check Prometheus metrics text format (with authentication)
    metrics_resp = client.get("/metrics", headers=headers)
    assert metrics_resp.status_code == 200
    metrics_text = metrics_resp.text
    
    # Verify policy evaluation latency histogram is present (C-044)
    # Metric name: policy_evaluation_latency_seconds (not policy_eval_latency_ms)
    assert "policy_evaluation_latency_seconds" in metrics_text
    assert "policy_evaluation_latency_seconds_bucket" in metrics_text
    
    # Verify companion counter is present
    assert "policy_evaluations_total" in metrics_text
    
    # Check metrics snapshot endpoint (with authentication)
    snapshot_resp = client.get("/api/v1/metrics/snapshot", headers=headers)
    assert snapshot_resp.status_code == 200
    snapshot = snapshot_resp.json()
    assert "metrics" in snapshot
    
    # Verify required metrics are present
    # Note: Prometheus histograms expose _bucket, _count, _sum, _created suffixes
    metric_names = snapshot["metrics"]
    assert any("policy_evaluation_latency_seconds" in m for m in metric_names)
    assert any("policy_evaluations_total" in m for m in metric_names)
