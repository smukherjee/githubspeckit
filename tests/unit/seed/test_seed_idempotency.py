from cli.bootstrap import bootstrap, deterministic_uuid


def test_seed_idempotency():
    # TEST-XCUT-07 deterministic UUIDv5 idempotency
    a = bootstrap()
    b = bootstrap()
    assert a.tenant_id == b.tenant_id
    assert a.admin_user_id == b.admin_user_id
    assert a.tenant_id == deterministic_uuid("tenant:primary")
