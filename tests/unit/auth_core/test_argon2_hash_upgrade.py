# TEST-AUTH-01: Argon2id hash/upgrade behavior (FR-049, FR-051, C-023, C-033)
# This is a failing-first test; it will pass once rehash detection triggers upgrade path logic in a service layer.

from auth_core.hashers import Argon2PasswordHasher, Argon2Params, default_hasher


def test_argon2_needs_rehash_on_param_strength_increase():
    weak_params = Argon2Params(time_cost=2)
    strong_params = Argon2Params(time_cost=3)
    weak_hasher = Argon2PasswordHasher(weak_params)
    strong_hasher = Argon2PasswordHasher(strong_params)

    password = "CorrectHorseBatteryStaple1"
    weak_hash = weak_hasher.hash(password)
    # strong hasher should signal that weak_hash needs rehash (time_cost difference)
    assert strong_hasher.needs_rehash(weak_hash) is True

    # Hash with strong parameters should not need rehash from strong perspective
    strong_hash = strong_hasher.hash(password)
    assert strong_hasher.needs_rehash(strong_hash) is False
