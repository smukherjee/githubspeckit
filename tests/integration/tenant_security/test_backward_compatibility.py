"""
Integration test: Backward compatibility for tenant_id query parameter (Quickstart Scenario 4).

Constitutional Compliance:
- Tests deprecation warning headers for legacy query parameters
- Validates sunset enforcement after deprecation period

Expected Result: ALL TESTS MUST PASS (deprecation middleware implemented).
"""

import pytest
import logging
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient
from adapters.api.app import create_app


@pytest.fixture
def client():
    """Create test client with deprecation middleware."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def authenticated_user(client, seeded_database):
    """Create and authenticate a test user."""
    # Login as standard user (seeded by seeded_database fixture)
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "infysightuser@infysight.com",
            "password": "infysightuser123"
        }
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    token = login_response.json()["access_token"]
    
    return {
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"}
    }


def test_query_param_deprecated_warning(client, authenticated_user, seeded_database):
    """Using tenant_id query parameter returns 200 OK + Deprecation header (before sunset)."""
    # Scenario: GET /users?tenant_id=X → 200 OK + Deprecation header
    
    # Use the user's own tenant_id to avoid cross-tenant rejection
    tenant_id = seeded_database["tenant_id"]
    headers = authenticated_user["headers"]
    
    # Make request with deprecated query parameter
    response = client.get(f"/api/v1/users?tenant_id={tenant_id}", headers=headers)
    
    # Should still succeed (before sunset date)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    # Verify deprecation headers present
    assert "deprecation" in response.headers, "Deprecation header missing"
    assert response.headers["deprecation"] == "true", f"Expected 'true', got {response.headers['deprecation']}"
    
    assert "sunset" in response.headers, "Sunset header missing"
    assert response.headers["sunset"] == "2025-11-19", f"Expected '2025-11-19', got {response.headers['sunset']}"
    
    assert "link" in response.headers, "Link header with migration guide missing"


def test_query_param_logged_warning(client, authenticated_user, seeded_database, caplog):
    """Using tenant_id query parameter logs WARNING-level message."""
    # Scenario: GET /users?tenant_id=X → Log entry created
    
    # Use the user's own tenant_id to avoid cross-tenant rejection
    tenant_id = seeded_database["tenant_id"]
    headers = authenticated_user["headers"]
    
    # Capture logs at WARNING level
    with caplog.at_level(logging.WARNING):
        # Make request with deprecated query parameter
        response = client.get(f"/api/v1/users?tenant_id={tenant_id}", headers=headers)
        
        # Should succeed
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    # Verify warning was logged
    warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
    assert len(warning_logs) > 0, "No WARNING logs captured"
    
    # Check for deprecation message
    deprecation_logs = [
        record for record in warning_logs 
        if "tenant_id query param" in record.message.lower()
    ]
    assert len(deprecation_logs) > 0, f"No deprecation warning found. Warnings: {[r.message for r in warning_logs]}"


def test_query_param_after_sunset(client, authenticated_user, seeded_database):
    """After sunset date (2025-11-19), tenant_id query parameter returns 400 Bad Request."""
    # Scenario: GET /users?tenant_id=X (after 2025-11-19) → 400 Bad Request
    
    # Use the user's own tenant_id to avoid cross-tenant rejection
    tenant_id = seeded_database["tenant_id"]
    headers = authenticated_user["headers"]
    
    # Mock current date as after sunset (2025-11-20)
    future_date = datetime(2025, 11, 20, tzinfo=datetime.now().astimezone().tzinfo)
    
    with patch('adapters.api.middleware.deprecation_warning.datetime') as mock_datetime:
        # Mock datetime.now() to return future date
        mock_datetime.now.return_value = future_date
        mock_datetime.fromisoformat = datetime.fromisoformat  # Keep original for parsing
        
        # Make request with deprecated query parameter
        response = client.get(f"/api/v1/users?tenant_id={tenant_id}", headers=headers)
        
        # Should be rejected after sunset
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        # Verify error message
        error_detail = response.json()
        assert "detail" in error_detail, f"No detail in error: {error_detail}"
        assert "no longer supported" in error_detail["detail"].lower(), f"Wrong error message: {error_detail['detail']}"
