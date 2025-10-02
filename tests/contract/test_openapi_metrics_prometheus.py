import pytest


def test_metrics_prometheus_contract_placeholder():
    pass


@pytest.mark.contract
def test_metrics_prometheus_exposes_tenant_labels():
    """Contract test: the /metrics endpoint must expose metrics that include a `tenant_id` label

    This test registers a sample counter on the app's prometheus adapter and asserts the
    scrape output includes the expected metric name and tenant label.
    """
    from fastapi.testclient import TestClient
    from adapters.api.app import create_app

    app = create_app()
    client = TestClient(app)

    # register a sample metric with tenant label via the PromClientAdapter on app.state
    # adapter name chosen: 'active_users'
    # active_users is a gauge; use gauge_set to avoid duplicate counter registration
    app.state.prom.gauge_set("active_users", tenant_id="t-xyz", value=3)

    resp = client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    # Expect metric name and label present
    assert "active_users" in text
    assert "tenant_id=\"t-xyz\"" in text
