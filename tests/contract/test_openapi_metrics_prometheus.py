import pytest


def test_metrics_prometheus_contract_placeholder():
    pass


@pytest.mark.contract
def test_metrics_prometheus_exposes_tenant_labels():
    """Contract test: the /metrics endpoint must expose metrics that include a `tenant_id` label

    This test registers a sample counter on the app's prometheus adapter and asserts the
    scrape output includes the expected metric name and tenant label.
    
    Note: This endpoint requires authentication as of V1.0 RBAC enforcement.
    """
    from fastapi.testclient import TestClient
    from adapters.api.app import create_app
    from auth_core.jwt import JWTService, JWTKeySet

    app = create_app()
    client = TestClient(app)
    
    # Create authenticated client with superadmin token
    jwt_keys = JWTKeySet(active_kid="v1", keys={"v1": "dev-secret-key"})
    jwt_service = JWTService(keys=jwt_keys, issuer="modern-backend", audience="modern-backend")
    
    # Generate superadmin token
    token = jwt_service.issue(
        sub="11111111-1111-1111-1111-111111111111",  # Superadmin user UUID
        tenant_id="00000000-0000-0000-0000-000000000000",  # Superadmin tenant UUID
        roles=["superadmin"],
        extra={}
    )
    
    headers = {"Authorization": f"Bearer {token}"}

    # register a sample metric with tenant label via the PromClientAdapter on app.state
    # adapter name chosen: 'active_users'
    # active_users is a gauge; use gauge_set to avoid duplicate counter registration
    app.state.prom.gauge_set("active_users", tenant_id="t-xyz", value=3)

    resp = client.get("/metrics", headers=headers)
    assert resp.status_code == 200
    text = resp.text
    # Expect metric name and label present
    assert "active_users" in text
    assert "tenant_id=\"t-xyz\"" in text
