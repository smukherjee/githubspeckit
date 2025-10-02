import pytest
from datetime import datetime, timedelta, timezone

# TEST-AUTH-13 Role downgrade session invalidation (FR-021, C-032)

from auth_core.jwt import JWTService, JWTKeySet
from auth_core.revocation import RevocationService
from auth_core.validator import TokenValidator, SessionInvalidatedError


def build():
    keys = JWTKeySet(active_kid="k1", keys={"k1": "secret-1"})
    svc = JWTService(keys=keys, issuer="speckit", audience="speckit-api", default_exp_minutes=10)
    rev = RevocationService()
    validator = TokenValidator(jwt_service=svc, revocations=rev)
    return svc, validator


def test_session_version_invalidation():
    svc, validator = build()
    now = datetime.now(timezone.utc)
    # Issue token with session version 1
    token = svc.issue(sub="u1", tenant_id="t1", roles=["standard"], session_version=1, now=now, expires_in=timedelta(minutes=5))
    # Validate with expected version 1 succeeds
    claims = validator.validate(token, audience="speckit-api", now=now, expected_session_version=1)
    assert claims["sv"] == 1
    # After downgrade bump session version to 2 -> token should fail
    with pytest.raises(SessionInvalidatedError):
        validator.validate(token, audience="speckit-api", now=now + timedelta(seconds=1), expected_session_version=2)
