import pytest
from fastapi.testclient import TestClient
from adapters.api.app import create_app
from services.invitations_service import InvitationService
from adapters.api.deps import get_invitation_repo


@pytest.mark.contract
def test_invitation_accept_contract_flow():
    app = create_app()
    client = TestClient(app)
    tr = client.post("/v1/tenants", json={"name": "InvitationFlow"})
    tenant_id = tr.json()["tenant_id"]
    repo = get_invitation_repo()
    svc = InvitationService(repo=repo)
    inv = svc.create_invitation(tenant_id=tenant_id, email="invflow@example.com", actor="system")

    ar = client.post(f"/v1/invitations/{inv.invitation_id}/accept")
    assert ar.status_code == 200
    data = ar.json()
    assert data["invitation_id"] == inv.invitation_id
    assert data["status"] == "accepted"
