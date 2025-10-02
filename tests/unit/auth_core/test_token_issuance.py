import pytest
from datetime import datetime, timedelta, timezone

# TEST-AUTH-03 Token issuance (FR-008)
# Drives minimal JWT service skeleton (IMPL-AUTH-04)

from auth_core.jwt import JWTService, JWTKeySet


def test_token_issuance_basic_claims():
    keys = JWTKeySet(
        active_kid="k1",
        keys={
            "k1": "secret-key-1",
        }
    )
    service = JWTService(keys=keys, issuer="speckit", audience="speckit-api", default_exp_minutes=15)
    now = datetime.now(timezone.utc)
    token = service.issue(sub="user-123", tenant_id="tenant-abc", roles=["tenant_admin"], now=now)
    decoded = service.decode(token, audience="speckit-api")
    assert decoded["sub"] == "user-123"
    assert decoded["tenant_id"] == "tenant-abc"
    assert decoded["roles"] == ["tenant_admin"]
    assert decoded["iss"] == "speckit"
    assert decoded["aud"] == "speckit-api"
    assert decoded["exp"] > decoded["iat"]
    assert decoded["kid"] == "k1"


def test_token_issuance_custom_expiry():
    keys = JWTKeySet(active_kid="k1", keys={"k1": "secret-key-1"})
    service = JWTService(keys=keys, issuer="speckit", audience="speckit-api", default_exp_minutes=15)
    now = datetime.now(timezone.utc)
    token = service.issue(sub="user-123", tenant_id="tenant-abc", roles=["tenant_admin"], now=now, expires_in=timedelta(minutes=60))
    decoded = service.decode(token, audience="speckit-api")
    assert decoded["exp"] - decoded["iat"] >= 60 * 60 - 1  # allow small clock diff


def test_token_rejects_wrong_audience():
    keys = JWTKeySet(active_kid="k1", keys={"k1": "secret-key-1"})
    service = JWTService(keys=keys, issuer="speckit", audience="speckit-api", default_exp_minutes=15)
    now = datetime.now(timezone.utc)
    token = service.issue(sub="user-123", tenant_id="tenant-abc", roles=["tenant_admin"], now=now)
    with pytest.raises(Exception):
        service.decode(token, audience="different-aud")
