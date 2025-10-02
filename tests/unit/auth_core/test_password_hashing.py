import pytest
from auth_core.providers.password import PasswordAuthProvider
from auth_core.hashers import default_hasher, Argon2PasswordHasher, Argon2Params

# TEST-AUTH-01: Argon2id hash & upgrade detection (FR-049, FR-051)

@pytest.mark.asyncio
async def test_password_auth_success_and_upgrade_needed():
    provider = PasswordAuthProvider()
    # Simulate stored hash with weaker params (time_cost=2) requiring upgrade to default (3)
    weaker = Argon2PasswordHasher(Argon2Params(time_cost=2)).hash("s3cret-pass")
    result = await provider.authenticate(username="user-123", password="s3cret-pass", stored_hash=weaker)
    assert result.user_id == "user-123"
    assert default_hasher.needs_rehash(weaker) is True
    # After upgrade new hash should not need rehash
    upgraded = default_hasher.hash("s3cret-pass")
    assert default_hasher.needs_rehash(upgraded) is False

@pytest.mark.asyncio
async def test_password_auth_invalid_credentials():
    provider = PasswordAuthProvider()
    stored = default_hasher.hash("correct")
    with pytest.raises(Exception) as exc:
        await provider.authenticate(username="user-1", password="wrong", stored_hash=stored)
    assert getattr(exc.value, "code", None) == "invalid_credentials"
