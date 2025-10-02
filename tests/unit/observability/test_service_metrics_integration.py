from adapters.observability.prometheus_client_adapter import PromClientAdapter
from services.user_lifecycle_service import UserLifecycleService


def test_user_lifecycle_emits_active_user_metrics():
    from domain.users.models import User, UserRepository, UserStatus

    registry = PromClientAdapter()
    # create repo and user
    repo = UserRepository()
    user = User(user_id="u-100", tenant_id="t-1", email="u100@example.com", status=UserStatus.active)
    repo.upsert(user)

    svc = UserLifecycleService(repo=repo, metrics_adapter=registry)

    # disable should decrement active_users (we don't track initial gauge; ensure calls produce labeled metrics)
    svc.disable("u-100", actor="admin")
    svc.restore("u-100", actor="admin")

    out = registry.generate_latest().decode("utf-8")
    assert "active_users" in out
    assert 'tenant_id="t-1"' in out
