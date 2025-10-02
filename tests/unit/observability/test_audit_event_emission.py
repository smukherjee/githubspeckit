import pytest

# TEST-OBS-12: Audit event emission for security-sensitive actions (FR-005)

def test_audit_event_emission_for_invite_and_user_actions():
    from services.audit_service import AuditService
    from services.invitations_service import InvitationService
    from services.user_lifecycle_service import UserLifecycleService
    from domain.invitations.models import Invitation, InvitationRepository, InvitationStatus
    from domain.users.models import UserRepository, User, UserStatus

    from datetime import datetime, timezone, timedelta

    audit = AuditService()
    # prepare repo and invitation
    repo = InvitationRepository()
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    inv = Invitation(invitation_id="inv-1", tenant_id="t-1", email="x@example.com", expires_at=expires)
    repo.upsert(inv)
    svc = InvitationService(repo=repo, audit_service=audit)
    svc.accept("inv-1", actor="tester")
    events = audit.query()
    assert any(e["action"] == "invitation.accept" and e["target"]["invitation_id"] == "inv-1" for e in events)

    # user lifecycle events
    urepo = UserRepository()
    user = User(user_id="u-1", tenant_id="t-1", email="u@example.com", status=UserStatus.active)
    urepo.upsert(user)
    ul = UserLifecycleService(repo=urepo, audit_service=audit)
    ul.disable("u-1", actor="admin")
    ul.restore("u-1", actor="admin")
    events = audit.query()
    assert any(e["action"] == "user.disable" and e["target"]["user_id"] == "u-1" for e in events)
    assert any(e["action"] == "user.restore" and e["target"]["user_id"] == "u-1" for e in events)
