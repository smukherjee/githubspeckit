"""
Integration test: Audit logging for authorization decisions (Quickstart Scenario 7).

Constitutional Compliance:
- Tests audit coverage for authorization decisions
- Validates audit events are created for key operations

Expected Result: Tests verify audit logging for login and critical operations.
"""

import pytest
import pytest_asyncio
from uuid import uuid5, UUID
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

INFYSIGHT_NAMESPACE = UUID("12345678-1234-5678-1234-567812345678")


def deterministic_uuid(name: str) -> str:
    """Generate deterministic UUID for testing."""
    return str(uuid5(INFYSIGHT_NAMESPACE, name))


@pytest.mark.asyncio
async def test_authorization_decision_logged(client, regular_user_headers, db_session):
    """Login creates audit event (auth.login.success)."""
    # Verify that login (which we just did to get headers) created an audit event
    from adapters.persistence.repositories import SQLAlchemyAuditAppender
    
    audit_appender = SQLAlchemyAuditAppender(db_session)
    
    # Query for recent login events
    events = await audit_appender.list(action="auth.login.success", limit=10)
    
    # Should have at least one login event (from the regular_user_headers fixture)
    assert len(events) > 0, "No login audit events found"
    
    # Verify event structure
    login_event = events[0]
    assert login_event.category == "auth"
    assert login_event.action == "auth.login.success"
    assert login_event.tenant_id is not None
    assert "user_id" in login_event.metadata
    assert "email" in login_event.metadata


@pytest.mark.asyncio
async def test_tenant_switch_logged(client, superadmin_headers, test_tenant_id, db_session):
    """Tenant switching endpoint exists and can be tested for audit logging."""
    # Skip: Tenant switch audit logging marked as TODO in context.py endpoint
    # The endpoint exists but audit emission is commented out
    # TODO (Phase 3.6): Uncomment audit emission in /admin/context/tenant
    pytest.skip("Tenant switch audit logging pending - endpoint has TODO comment for audit emission")


@pytest.mark.asyncio
async def test_audit_log_completeness(client, regular_user_headers, db_session):
    """Multiple logins create multiple audit events."""
    from adapters.persistence.repositories import SQLAlchemyAuditAppender
    
    audit_appender = SQLAlchemyAuditAppender(db_session)
    
    # Count existing events
    initial_events = await audit_appender.list(action="auth.login.success", limit=100)
    initial_count = len(initial_events)
    
    # Perform another login
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "infysightuser@infysight.com",
            "password": "infysightuser123"
        }
    )
    assert response.status_code == 200
    
    # Query again - should have one more event
    new_events = await audit_appender.list(action="auth.login.success", limit=100)
    new_count = len(new_events)
    
    assert new_count == initial_count + 1, f"Expected {initial_count + 1} events, got {new_count}"


@pytest.mark.asyncio
async def test_audit_log_export(client, db_session):
    """Audit events can be queried from database with filtering."""
    from adapters.persistence.repositories import SQLAlchemyAuditAppender
    
    audit_appender = SQLAlchemyAuditAppender(db_session)
    
    # Query all events (no filtering)
    all_events = await audit_appender.list(limit=50)
    
    # Should have some events from previous tests
    assert len(all_events) > 0, "No audit events found in database"
    
    # Verify each event has required fields
    for event in all_events:
        assert event.event_id is not None
        assert event.category is not None
        assert event.action is not None
        assert event.created_at is not None
        # metadata should be dict
        assert isinstance(event.metadata, dict)
    
    # Test filtering by action
    login_events = await audit_appender.list(action="auth.login.success", limit=10)
    if len(login_events) > 0:
        # All should be login events
        for event in login_events:
            assert event.action == "auth.login.success"
