import pytest
from adapters.observability.prometheus_client_adapter import PromClientAdapter
from services.invitations_service import InvitationService


@pytest.mark.asyncio
async def test_invitation_service_emits_auth_failure_metric_on_missing():
    from domain.invitations.models import InvitationRepository

    prom = PromClientAdapter()
    repo = InvitationRepository()
    # do not insert an invitation; attempt to accept triggers missing
    svc = InvitationService(repo=repo, metrics_adapter=prom)
    try:
        await svc.accept("does-not-exist", actor="tester")  # Convert to await
    except KeyError:
        pass

    out = prom.generate_latest().decode("utf-8")
    assert "auth_failures_total" in out
