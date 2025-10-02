import pytest
from auth_core import AuthenticationService, default_registry, MFACodeRequiredError
from auth_core.hashers import default_hasher

# TEST-AUTH-09 Login + MFA branch (FR-061/FR-062 subset) -- MFA enforcement only

PASSWORD = "Secur3Passw0rd!"
HASH = default_hasher.hash(PASSWORD)


@pytest.mark.asyncio
async def test_login_password_basic_no_mfa():
    svc = AuthenticationService(registry=default_registry())
    result = await svc.login_password(user_id="user-1", stored_hash=HASH, password=PASSWORD, user_has_mfa=False)
    assert result["user_id"] == "user-1"
    assert result["needs_rehash"] in (True, False)


@pytest.mark.asyncio
async def test_login_password_mfa_required_branch():
    svc = AuthenticationService(registry=default_registry())
    with pytest.raises(MFACodeRequiredError):
        await svc.login_password(user_id="user-2", stored_hash=HASH, password=PASSWORD, user_has_mfa=True)
