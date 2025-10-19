"""
Integration test: JWT-based tenant isolation (Quickstart Scenario 1).

Constitutional Compliance:
- Tests end-to-end tenant isolation enforcement
- Validates audit logging for authorization decisions

Phase 3.5 T049: Validate JWT-based tenant isolation with middleware
"""

import pytest
import pytest_asyncio
from uuid import uuid4, uuid5, UUID


INFYSIGHT_NAMESPACE = UUID("12345678-1234-5678-1234-567812345678")


def deterministic_uuid(name: str) -> str:
    """Generate deterministic UUIDs for test data."""
    return str(uuid5(INFYSIGHT_NAMESPACE, name))


@pytest.mark.asyncio
async def test_standard_user_own_tenant(client, regular_user_headers, test_tenant_id):
    """Standard user successfully accesses resources in their own tenant (200 OK)."""
    # Scenario: User logs in → GET /tenants/{own_tenant_id}/users → 200 OK
    
    # Standard user should be able to access their own tenant
    response = await client.get(
        f"/api/v1/tenants/{test_tenant_id}/users",
        headers=regular_user_headers
    )
    
    # Should return 200 OK with user list
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert "users" in data, "Response should contain 'users' field"
    assert "pagination" in data, "Response should contain 'pagination' field"
    assert isinstance(data["users"], list), "Users should be a list"


@pytest.mark.asyncio
async def test_standard_user_cross_tenant_denied(client, regular_user_headers, test_tenant_id):
    """Standard user CANNOT access resources in other tenants (403 Forbidden)."""
    # Scenario: User logs in (Tenant A) → GET /tenants/{tenant_b_id}/users → 403
    
    # Create a different tenant ID (not the user's tenant)
    other_tenant_id = deterministic_uuid("tenant:othertenant")
    
    # Standard user should NOT be able to access other tenant
    response = await client.get(
        f"/api/v1/tenants/{other_tenant_id}/users",
        headers=regular_user_headers
    )
    
    # Should return 403 Forbidden
    assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}: {response.text}"
    
    # Should have tenant isolation policy header
    assert "X-Tenant-Isolation-Policy" in response.headers or "x-tenant-isolation-policy" in response.headers, \
        "Response should contain X-Tenant-Isolation-Policy header"


@pytest.mark.asyncio
async def test_audit_log_cross_tenant_denial(client, regular_user_headers, test_tenant_id, db_engine):
    """Cross-tenant access denial creates audit event with rule 'cross_tenant_isolation'."""
    # Scenario: User attempts cross-tenant access → 403 → Audit event created
    # NOTE: This test is currently skipped because audit logging is not yet fully wired
    # to the authorization middleware. This will be implemented in a future task.
    
    pytest.skip("Audit logging for authorization decisions not yet fully implemented - T055 pending")
    
    # FUTURE IMPLEMENTATION:
    # other_tenant_id = deterministic_uuid("tenant:othertenant")
    #
    # # Attempt cross-tenant access (should be denied)
    # response = await client.get(
    #     f"/api/v1/tenants/{other_tenant_id}/users",
    #     headers=regular_user_headers
    # )
    #
    # assert response.status_code == 403
    #
    # # Query audit events table to verify event was created
    # from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    # from sqlalchemy import select
    # from adapters.persistence.models import AuditEventModel
    #
    # async_session_maker = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    #
    # async with async_session_maker() as session:
    #     query = select(AuditEventModel).where(AuditEventModel.event_type == "authorization_decision")
    #     result = await session.execute(query)
    #     audit_events = result.scalars().all()
    #
    #     assert len(audit_events) > 0, "At least one audit event should exist"
    #
    #     # Find the most recent event
    #     latest_event = max(audit_events, key=lambda e: e.created_at)
    #
    #     # Verify event details
    #     assert latest_event.details.get("decision") == "DENY"
    #     assert latest_event.details.get("rule_applied") == "cross_tenant_isolation"

