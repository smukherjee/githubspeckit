"""TEST-API-11 Invitation accept endpoint flow (basic contract).
Uses existing invitation service create side manually (simulate) then accept via API route.
"""
from fastapi.testclient import TestClient
from adapters.api.app import create_app
from services.invitations_service import InvitationService
from adapters.api.deps import get_invitation_service, get_invitation_repo
from uuid import uuid4


def test_invitation_accept_flow():
    app = create_app()
    client = TestClient(app)
    # create tenant
    tr = client.post("/v1/tenants", json={"name": "InviteCo"})
    tenant_id = tr.json()["tenant_id"]
    # Simulate invitation creation via service (not yet exposed) - we rely on service API
    # Use the DI singletons so API route sees same repo
    repo = get_invitation_repo()
    svc = InvitationService(repo=repo)
    inv = svc.create_invitation(tenant_id=tenant_id, email="newuser@example.com", actor="system")
    # Accept via API should 200
    ar = client.post(f"/v1/invitations/{inv.invitation_id}/accept")
    assert ar.status_code == 200
    data = ar.json()
    assert data["status"] == "accepted"
    assert data["invitation_id"] == inv.invitation_id
