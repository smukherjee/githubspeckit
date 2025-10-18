from datetime import datetime, timezone

from domain.tenants.models import Tenant, TenantRepository, TenantStatus
from domain.users.models import User, UserRepository, UserStatus

# TEST-DOM-07: Soft delete/restore invariants (FR-018)

def test_soft_delete_restore_invariants_tenant_and_user():
    tenant_repo = TenantRepository()
    user_repo = UserRepository()

    tenant = Tenant(tenant_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", name="Acme", created_by="system", updated_by="system")
    tenant_repo.upsert(tenant)
    user = User(user_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", tenant_id=tenant.tenant_id, email="user@example.com", created_by="system", updated_by="system")
    user_repo.upsert(user)

    original_tenant_updated = tenant.updated_at
    original_user_updated = user.updated_at

    tenant_repo.soft_delete(tenant.tenant_id)
    user_repo.soft_delete(user.user_id)
    assert tenant.status == TenantStatus.disabled
    assert user.status == UserStatus.disabled
    assert tenant.updated_at > original_tenant_updated
    assert user.updated_at > original_user_updated

    # restore
    tenant_repo.restore(tenant.tenant_id)
    user_repo.restore(user.user_id)
    assert tenant.status == TenantStatus.active
    assert user.status == UserStatus.active
    assert tenant.updated_at > original_tenant_updated
    assert user.updated_at > original_user_updated
    # identifiers unchanged
    assert tenant.tenant_id == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert user.user_id == "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
