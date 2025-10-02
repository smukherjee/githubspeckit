"""TEST-API-25 Bootstrap command integration basic test.
Ensures bootstrap() returns deterministic ids across invocations.
"""
from cli.bootstrap import bootstrap, deterministic_uuid


def test_bootstrap_deterministic_ids():
    first = bootstrap()
    second = bootstrap()  # idempotent
    assert first.tenant_id == second.tenant_id
    assert first.admin_user_id == second.admin_user_id
    assert deterministic_uuid("tenant:primary") == first.tenant_id
