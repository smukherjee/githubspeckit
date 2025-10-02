import pytest
from datetime import datetime, timedelta, timezone
from auth_core.password_reset import PasswordResetService, PasswordResetError

# TEST-AUTH-11 Password reset lifecycle (FR-060..FR-065)


def test_password_reset_lifecycle_success():
    svc = PasswordResetService(default_exp_minutes=1)
    token = svc.initiate("user-1", now=datetime.now(timezone.utc))
    user_id = svc.complete(token, now=datetime.now(timezone.utc) + timedelta(seconds=10))
    assert user_id == "user-1"
    # Reuse should fail
    with pytest.raises(PasswordResetError):
        svc.complete(token, now=datetime.now(timezone.utc) + timedelta(seconds=20))


def test_password_reset_expired():
    svc = PasswordResetService(default_exp_minutes=0)  # immediate expiry
    token = svc.initiate("user-2", now=datetime.now(timezone.utc))
    with pytest.raises(PasswordResetError):
        svc.complete(token, now=datetime.now(timezone.utc) + timedelta(minutes=1))
