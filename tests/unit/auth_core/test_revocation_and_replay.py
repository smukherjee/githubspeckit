import pytest
from datetime import datetime, timedelta, timezone

# TEST-AUTH-07 Revocation & replay detection (FR-028, FR-033, C-020, C-027)

from auth_core.jwt import JWTService, JWTKeySet
from auth_core.revocation import RevocationService, TokenReplayError
from auth_core.validator import TokenValidator


def build_jwt():
    keys = JWTKeySet(active_kid="k1", keys={"k1": "secret-1"})
    return JWTService(keys=keys, issuer="speckit", audience="speckit-api", default_exp_minutes=1)


def test_replay_detection():
    svc = build_jwt()
    rev = RevocationService()
    validator = TokenValidator(jwt_service=svc, revocations=rev)
    now = datetime.now(timezone.utc)
    token = svc.issue(sub="u1", tenant_id="t1", roles=["standard"], now=now, expires_in=timedelta(minutes=5))
    # First validation registers jti
    claims1 = validator.validate(token, audience="speckit-api", now=now)
    assert claims1["sub"] == "u1"
    # Second validation should raise replay
    with pytest.raises(TokenReplayError):
        validator.validate(token, audience="speckit-api", now=now + timedelta(seconds=1))


def test_revocation_blocks_future_validations():
    svc = build_jwt()
    rev = RevocationService()
    validator = TokenValidator(jwt_service=svc, revocations=rev)
    now = datetime.now(timezone.utc)
    token = svc.issue(sub="u1", tenant_id="t1", roles=["standard"], now=now, expires_in=timedelta(minutes=5))
    claims = svc.decode(token, audience="speckit-api", now=now)
    jti = claims["jti"]
    # Revoke explicitly
    rev.revoke(jti=jti, ttl_seconds=300, reason="user_logout", now=now)
    with pytest.raises(Exception):
        validator.validate(token, audience="speckit-api", now=now + timedelta(seconds=1))
