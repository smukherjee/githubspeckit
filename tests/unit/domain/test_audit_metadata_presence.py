import re
from datetime import datetime, timezone, timedelta

from domain.tenants.models import Tenant, TenantStatus, TenantRepository
from domain.users.models import User, UserRepository
from domain.policy.models import Policy, PolicyRepository
from domain.featureflags.models import FeatureFlag, FeatureFlagRepository, FlagState
from domain.invitations.models import Invitation, InvitationRepository

UUID_RE = re.compile(r"^[0-9a-fA-F-]{36}$")

def test_audit_metadata_presence_across_domain_entities():
    tenant_repo = TenantRepository()
    user_repo = UserRepository()
    policy_repo = PolicyRepository()
    flag_repo = FeatureFlagRepository()
    invitation_repo = InvitationRepository()

    tenant = Tenant(tenant_id="11111111-1111-1111-1111-111111111111", name="Acme", status=TenantStatus.active, created_by="system", updated_by="system")
    tenant_repo.upsert(tenant)

    user = User(user_id="22222222-2222-2222-2222-222222222222", tenant_id=tenant.tenant_id, email="alice@example.com", created_by="system", updated_by="system")
    user_repo.upsert(user)

    policy = Policy(policy_id="33333333-3333-3333-3333-333333333333", tenant_id=tenant.tenant_id, name="Default", created_by="system", updated_by="system")
    policy_repo.upsert(policy)

    flag = FeatureFlag(flag_id="44444444-4444-4444-4444-444444444444", tenant_id=tenant.tenant_id, key="new-ui", state=FlagState.disabled, created_by="system", updated_by="system")
    flag_repo.upsert(flag)

    invitation = Invitation(invitation_id="55555555-5555-5555-5555-555555555555", tenant_id=tenant.tenant_id, email="invitee@example.com", expires_at=datetime.now(timezone.utc)+timedelta(days=1), created_by="system", updated_by="system")
    invitation_repo.upsert(invitation)

    for obj, id_attr in [
        (tenant, 'tenant_id'),
        (user, 'user_id'),
        (policy, 'policy_id'),
        (flag, 'flag_id'),
        (invitation, 'invitation_id'),
    ]:
        assert getattr(obj, id_attr)
        # Audit fields present & timezone-aware UTC
        assert obj.created_at.tzinfo is not None and obj.created_at.tzinfo.utcoffset(obj.created_at) == timezone.utc.utcoffset(obj.created_at)
        assert obj.updated_at.tzinfo is not None and obj.updated_at.tzinfo.utcoffset(obj.updated_at) == timezone.utc.utcoffset(obj.updated_at)
        assert isinstance(obj.created_by, str)
        assert isinstance(obj.updated_by, str)
        assert UUID_RE.match(getattr(obj, id_attr))

