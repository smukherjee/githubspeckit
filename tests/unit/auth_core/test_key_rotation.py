import pytest
from datetime import datetime, timedelta, timezone

# TEST-AUTH-05 Key rotation grace (FR-022, C-028)
# Drives rotation orchestrator logic in JWTKeySet/JWTService (IMPL-AUTH-06)

from auth_core.jwt import JWTService, JWTKeySet


def build_service():
    keys = JWTKeySet(active_kid="k1", keys={"k1": "secret-1"})
    service = JWTService(keys=keys, issuer="speckit", audience="speckit-api", default_exp_minutes=5)
    return service


def test_key_rotation_grace_allows_old_token_until_expiry():
    svc = build_service()
    now = datetime.now(timezone.utc)
    # Issue token with initial key k1
    token_old = svc.issue(sub="u1", tenant_id="t1", roles=["tenant_admin"], now=now, expires_in=timedelta(minutes=30))
    # Rotate to new key k2 with 10 minute grace
    svc.keys.rotate(new_kid="k2", new_secret="secret-2", now=now, grace_minutes=10)

    # Issue token with new key
    token_new = svc.issue(sub="u1", tenant_id="t1", roles=["tenant_admin"], now=now + timedelta(seconds=5))

    # Both tokens validate during grace
    decoded_old = svc.decode(token_old, audience="speckit-api", now=now + timedelta(minutes=5))
    decoded_new = svc.decode(token_new, audience="speckit-api", now=now + timedelta(minutes=5))
    assert decoded_old["kid"] == "k1"
    assert decoded_new["kid"] == "k2"

    # After grace, old key pruned; old token should fail (even if not expired yet)
    after_grace = now + timedelta(minutes=11)
    with pytest.raises(Exception):
        svc.decode(token_old, audience="speckit-api", now=after_grace)

    # New token still validates
    decoded_new_late = svc.decode(token_new, audience="speckit-api", now=after_grace)
    assert decoded_new_late["kid"] == "k2"


def test_rotate_rejects_duplicate_kid():
    svc = build_service()
    with pytest.raises(ValueError):
        svc.keys.rotate(new_kid="k1", new_secret="another", now=datetime.now(timezone.utc))
