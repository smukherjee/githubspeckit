from dataclasses import dataclass

from domain.tenants.models import Tenant, TenantRepository
from domain.users.models import User, UserRepository

# TEST-DOM-05: Tenant isolation & superadmin bypass (FR-002, FR-011)

SUPERADMIN_ROLE = "superadmin"

def list_users_scoped(user_repo: UserRepository, requesting_user: User, tenant_id: str):
    if SUPERADMIN_ROLE in requesting_user.roles:
        # cross-tenant view: gather users across all tenant_ids present
        # naive approach: iterate underlying store
        return [u for u in user_repo._store.values()]  # accessing internal store acceptable for test scope
    return user_repo.list_by_tenant(tenant_id)

def test_tenant_isolation_and_superadmin_bypass():
    tenant_repo = TenantRepository()
    user_repo = UserRepository()

    t1 = Tenant(tenant_id="11111111-1111-1111-1111-111111111111", name="T1")
    t2 = Tenant(tenant_id="22222222-2222-2222-2222-222222222222", name="T2")
    tenant_repo.upsert(t1)
    tenant_repo.upsert(t2)

    u1 = User(user_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", tenant_id=t1.tenant_id, email="u1@example.com")
    u2 = User(user_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", tenant_id=t2.tenant_id, email="u2@example.com")
    user_repo.upsert(u1)
    user_repo.upsert(u2)

    normal_requester = User(user_id="cccccccc-cccc-cccc-cccc-cccccccccccc", tenant_id=t1.tenant_id, email="nr@example.com")
    superadmin_requester = User(user_id="dddddddd-dddd-dddd-dddd-dddddddddddd", tenant_id=t1.tenant_id, email="sa@example.com", roles=[SUPERADMIN_ROLE])
    user_repo.upsert(normal_requester)
    user_repo.upsert(superadmin_requester)

    scoped_normal = list_users_scoped(user_repo, normal_requester, t1.tenant_id)
    assert all(u.tenant_id == t1.tenant_id for u in scoped_normal)
    assert u2 not in scoped_normal

    # Simulated bypass: we expect ability to see cross-tenant user (u2)
    all_for_superadmin = list_users_scoped(user_repo, superadmin_requester, t1.tenant_id)
    assert u2 in all_for_superadmin
