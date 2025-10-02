import pytest
from domain.users.models import User, UserRepository, UserStatus
from services.user_lifecycle_service import UserLifecycleService


def test_soft_delete_and_restore_flow():
    repo = UserRepository()
    user = User(user_id="u1", tenant_id="t1", email="a@ex.com", status=UserStatus.active)
    repo.upsert(user)
    svc = UserLifecycleService(repo)
    disabled = svc.disable("u1", actor="admin")
    assert disabled.status == UserStatus.disabled
    restored = svc.restore("u1", actor="admin")
    assert restored.status == UserStatus.active


def test_restore_when_not_disabled_fails():
    repo = UserRepository()
    user = User(user_id="u2", tenant_id="t1", email="b@ex.com", status=UserStatus.active)
    repo.upsert(user)
    svc = UserLifecycleService(repo)
    with pytest.raises(ValueError):
        svc.restore("u2", actor="admin")
