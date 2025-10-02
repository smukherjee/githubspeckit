import pytest
from datetime import datetime, timezone, timedelta

from domain.invitations.models import Invitation, InvitationRepository, InvitationStatus
from services.invitations_service import InvitationService


def test_invitation_accept_idempotent():
    repo = InvitationRepository()
    now = datetime.now(timezone.utc)
    inv = Invitation(invitation_id="inv-1", tenant_id="t1", email="a@example.com", expires_at=now + timedelta(hours=1))
    repo.upsert(inv)
    svc = InvitationService(repo)
    accepted = svc.accept("inv-1", actor="system")
    assert accepted.status == InvitationStatus.accepted
    # second accept is idempotent and returns same accepted invitation
    again = svc.accept("inv-1", actor="system")
    assert again.status == InvitationStatus.accepted


def test_accept_nonexistent_raises():
    svc = InvitationService()
    with pytest.raises(KeyError):
        svc.accept("nope", actor="x")
