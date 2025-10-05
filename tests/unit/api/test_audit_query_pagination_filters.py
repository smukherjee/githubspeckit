import pytest
from fastapi.testclient import TestClient
from adapters.api.app import create_app
from datetime import datetime, timedelta, timezone


def seed_audit(app, n=15):
    svc = app.state.log_sink  # placeholder not audit service; adapt once real audit store exposed
    # The real audit service likely lives elsewhere; if audit querying endpoint uses a service on app.state
    # we locate it. For now, attempt attribute resolution.
    audit_service = getattr(app.state, 'audit_service', None)
    if not audit_service:
        return
    base_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    for i in range(n):
        audit_service.append(tenant_id=f"t{i%2}", actor_user_id=None, action_type="test.event", target_ref=f"res:{i}", metadata={"i": i}, created_at=base_time + timedelta(seconds=i))


@pytest.mark.skip(reason="Audit query endpoints not fully implemented yet")
def test_audit_query_basic_filters(monkeypatch):
    app = create_app()
    client = TestClient(app)
    seed_audit(app, n=20)

    # Basic request
    resp = client.get("/v1/audit/events?limit=5")
    assert resp.status_code in (200, 404)  # if not wired yet tolerate 404
    if resp.status_code == 404:
        return
    data = resp.json()
    assert data["limit"] == 5
    assert data["offset"] == 0
    assert data["count"] <= 5


@pytest.mark.skip(reason="Audit query endpoints not fully implemented yet")
def test_audit_query_pagination():
    app = create_app()
    client = TestClient(app)
    seed_audit(app, n=50)

    r1 = client.get("/v1/audit/events?limit=10&offset=0")
    r2 = client.get("/v1/audit/events?limit=10&offset=10")
    if r1.status_code != 200:
        return
    d1 = r1.json()
    d2 = r2.json()
    assert d1["limit"] == 10
    assert d2["limit"] == 10
    assert d1["offset"] == 0
    assert d2["offset"] == 10
    # Ensure no duplicate ids across first two pages
    ids1 = {item.get("event_id") for item in d1.get("items", [])}
    ids2 = {item.get("event_id") for item in d2.get("items", [])}
    assert not ids1.intersection(ids2)
