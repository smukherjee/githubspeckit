import pytest

# TEST-AUTH-17 MFA verify_code pass-through (no factors enrolled) (FR-061/FR-062)

from auth_core import AuthenticationService, default_registry
from auth_core.hashers import default_hasher

PASSWORD = "Secur3Passw0rd!"
HASH = default_hasher.hash(PASSWORD)


@pytest.mark.asyncio
async def test_mfa_pass_through_when_not_enrolled():
    svc = AuthenticationService(registry=default_registry())
    result = await svc.login_password(user_id="u1", stored_hash=HASH, password=PASSWORD, user_has_mfa=False)
    assert result["user_id"] == "u1"
