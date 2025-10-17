"""
Contract tests for admin audit event endpoints.
Tests API shape, request/response schemas, and status codes.
These tests MUST FAIL until implementation is complete.
"""
import pytest
from httpx import AsyncClient
from fastapi import status


class TestAdminAuditEventContracts:
    """Contract tests for /api/v1/admin/audit-events endpoints."""

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_list_audit_events_contract(self, client: AsyncClient, superadmin_headers):
        """Test GET /api/v1/admin/audit-events contract."""
        response = await client.get("/api/v1/admin/audit-events", headers=superadmin_headers)
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)
        
        # If data exists, validate audit event structure
        if data["data"]:
            event = data["data"][0]
            required_fields = [
                "event_id", "tenant_id", "user_id", "action", "resource_type",
                "resource_id", "details", "ip_address", "user_agent",
                "timestamp", "severity", "tags"
            ]
            for field in required_fields:
                assert field in event
            
            # Validate enums and types
            assert event["action"] in [
                "CREATE", "READ", "UPDATE", "DELETE", "LOGIN", "LOGOUT",
                "INVITE", "ACCEPT_INVITE", "REVOKE_INVITE", "ENABLE", "DISABLE"
            ]
            assert event["resource_type"] in [
                "tenant", "user", "policy", "feature_flag", "invitation", "audit_event"
            ]
            assert event["severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            assert isinstance(event["details"], dict) or event["details"] is None
            assert isinstance(event["tags"], list) or event["tags"] is None

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_list_audit_events_with_filters_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id, test_user_id):
        """Test GET /api/v1/admin/audit-events with filters."""
        params = {
            "tenant_id": test_tenant_id,
            "user_id": test_user_id,
            "action": "CREATE",
            "resource_type": "user",
            "severity": "MEDIUM",
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-12-31T23:59:59Z",
            "page": 1,
            "per_page": 20
        }
        
        response = await client.get(
            "/api/v1/admin/audit-events",
            headers=superadmin_headers,
            params=params
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # All events should match filters
        for event in data["data"]:
            assert event["tenant_id"] == test_tenant_id
            assert event["user_id"] == test_user_id
            assert event["action"] == "CREATE"
            assert event["resource_type"] == "user"
            assert event["severity"] == "MEDIUM"

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_list_audit_events_date_range_contract(self, client: AsyncClient, superadmin_headers):
        """Test GET /api/v1/admin/audit-events with date range filtering."""
        params = {
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-01-31T23:59:59Z"
        }
        
        response = await client.get(
            "/api/v1/admin/audit-events",
            headers=superadmin_headers,
            params=params
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # All events should be within date range
        for event in data["data"]:
            timestamp = event["timestamp"]
            assert timestamp >= params["start_date"]
            assert timestamp <= params["end_date"]

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_create_audit_event_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id, test_user_id):
        """Test POST /api/v1/admin/audit-events contract."""
        event_data = {
            "user_id": test_user_id,
            "action": "UPDATE",
            "resource_type": "user",
            "resource_id": test_user_id,
            "details": {
                "changed_fields": ["email", "full_name"],
                "old_values": {
                    "email": "old.email@example.com",
                    "full_name": "Old Name"
                },
                "new_values": {
                    "email": "new.email@example.com",
                    "full_name": "New Name"
                }
            },
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 (Test Browser)",
            "severity": "MEDIUM",
            "tags": ["user_management", "profile_update"]
        }
        
        response = await client.post(
            "/api/v1/admin/audit-events",
            headers=superadmin_headers,
            params={"tenant_id": test_tenant_id},
            json=event_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        assert "data" in data
        event = data["data"]
        
        # Required fields
        assert "event_id" in event
        assert event["tenant_id"] == test_tenant_id
        assert event["user_id"] == event_data["user_id"]
        assert event["action"] == event_data["action"]
        assert event["resource_type"] == event_data["resource_type"]
        assert event["resource_id"] == event_data["resource_id"]
        assert event["details"] == event_data["details"]
        assert event["ip_address"] == event_data["ip_address"]
        assert event["user_agent"] == event_data["user_agent"]
        assert event["severity"] == event_data["severity"]
        assert event["tags"] == event_data["tags"]
        
        # timestamp should be generated
        assert "timestamp" in event
        assert event["timestamp"] is not None

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_create_audit_event_minimal_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id, test_user_id):
        """Test POST /api/v1/admin/audit-events with minimal required fields."""
        event_data = {
            "user_id": test_user_id,
            "action": "LOGIN",
            "resource_type": "user"
        }
        
        response = await client.post(
            "/api/v1/admin/audit-events",
            headers=superadmin_headers,
            params={"tenant_id": test_tenant_id},
            json=event_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        event = data["data"]
        
        # Default values should be applied
        assert event["severity"] == "LOW"  # Default severity
        assert event["details"] is None or event["details"] == {}
        assert event["tags"] is None or event["tags"] == []

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_create_audit_event_validation_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test POST /api/v1/admin/audit-events validation contract."""
        # Invalid action
        invalid_data = {
            "user_id": "22222222-2222-2222-2222-222222222222",
            "action": "INVALID_ACTION",  # Invalid
            "resource_type": "user"
        }
        
        response = await client.post(
            "/api/v1/admin/audit-events",
            headers=superadmin_headers,
            params={"tenant_id": test_tenant_id},
            json=invalid_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_get_audit_event_by_id_contract(self, client: AsyncClient, superadmin_headers, test_audit_event_id):
        """Test GET /api/v1/admin/audit-events/{event_id} contract."""
        response = await client.get(
            f"/api/v1/admin/audit-events/{test_audit_event_id}",
            headers=superadmin_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "data" in data
        event = data["data"]
        assert event["event_id"] == test_audit_event_id

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_audit_events_immutable_contract(self, client: AsyncClient, superadmin_headers, test_audit_event_id):
        """Test that audit events cannot be updated (immutable)."""
        update_data = {
            "action": "DELETE",
            "severity": "HIGH"
        }
        
        response = await client.put(
            f"/api/v1/admin/audit-events/{test_audit_event_id}",
            headers=superadmin_headers,
            json=update_data
        )
        
        # Audit events should be immutable
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_audit_events_no_delete_contract(self, client: AsyncClient, superadmin_headers, test_audit_event_id):
        """Test that audit events cannot be deleted (immutable)."""
        response = await client.delete(
            f"/api/v1/admin/audit-events/{test_audit_event_id}",
            headers=superadmin_headers
        )
        
        # Audit events should be immutable
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_export_audit_events_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test POST /api/v1/admin/audit-events/export contract."""
        export_data = {
            "format": "CSV",
            "filters": {
                "tenant_id": test_tenant_id,
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-12-31T23:59:59Z",
                "actions": ["CREATE", "UPDATE", "DELETE"],
                "resource_types": ["user", "tenant"]
            },
            "fields": [
                "timestamp", "user_id", "action", "resource_type",
                "resource_id", "ip_address", "severity"
            ]
        }
        
        response = await client.post(
            "/api/v1/admin/audit-events/export",
            headers=superadmin_headers,
            json=export_data
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        
        data = response.json()
        assert "export_id" in data
        assert "status" in data
        assert data["status"] == "PROCESSING"

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_export_audit_events_json_contract(self, client: AsyncClient, superadmin_headers):
        """Test POST /api/v1/admin/audit-events/export with JSON format."""
        export_data = {
            "format": "JSON",
            "filters": {
                "severity": "HIGH",
                "start_date": "2024-01-01T00:00:00Z"
            }
        }
        
        response = await client.post(
            "/api/v1/admin/audit-events/export",
            headers=superadmin_headers,
            json=export_data
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["status"] == "PROCESSING"

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_get_export_status_contract(self, client: AsyncClient, superadmin_headers):
        """Test GET /api/v1/admin/audit-events/exports/{export_id} contract."""
        test_export_id = "33333333-3333-3333-3333-333333333333"
        
        response = await client.get(
            f"/api/v1/admin/audit-events/exports/{test_export_id}",
            headers=superadmin_headers
        )
        
        # Should fail until implemented
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_200_OK]
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "status" in data
            assert data["status"] in ["PROCESSING", "COMPLETED", "FAILED"]

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_tenant_admin_list_audit_events_scoped_contract(self, client: AsyncClient, tenant_admin_headers):
        """Test that tenant_admin can only see audit events in their tenant."""
        response = await client.get("/api/v1/admin/audit-events", headers=tenant_admin_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # All events should belong to the same tenant
        if data["data"]:
            tenant_id = data["data"][0]["tenant_id"]
            for event in data["data"]:
                assert event["tenant_id"] == tenant_id

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_tenant_admin_cross_tenant_audit_forbidden_contract(
        self, client: AsyncClient, tenant_admin_headers
    ):
        """Test that tenant_admin cannot create audit events for other tenants."""
        other_tenant_id = "11111111-1111-1111-1111-111111111111"
        event_data = {
            "user_id": "22222222-2222-2222-2222-222222222222",
            "action": "CREATE",
            "resource_type": "user"
        }
        
        response = await client.post(
            "/api/v1/admin/audit-events",
            headers=tenant_admin_headers,
            params={"tenant_id": other_tenant_id},
            json=event_data
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_standard_user_access_forbidden_contract(self, client: AsyncClient, user_headers):
        """Test that standard users cannot access admin audit event endpoints."""
        response = await client.get("/api/v1/admin/audit-events", headers=user_headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_unauthenticated_access_contract(self, client: AsyncClient):
        """Test that unauthenticated requests are rejected."""
        response = await client.get("/api/v1/admin/audit-events")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_audit_search_contract(self, client: AsyncClient, superadmin_headers):
        """Test POST /api/v1/admin/audit-events/search contract."""
        search_data = {
            "query": "user creation",
            "filters": {
                "actions": ["CREATE"],
                "resource_types": ["user"],
                "severity": "MEDIUM"
            },
            "sort_by": "timestamp",
            "sort_order": "DESC",
            "page": 1,
            "per_page": 10
        }
        
        response = await client.post(
            "/api/v1/admin/audit-events/search",
            headers=superadmin_headers,
            json=search_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_audit_statistics_contract(self, client: AsyncClient, superadmin_headers, test_tenant_id):
        """Test GET /api/v1/admin/audit-events/statistics contract."""
        params = {
            "tenant_id": test_tenant_id,
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-12-31T23:59:59Z",
            "group_by": "action"
        }
        
        response = await client.get(
            "/api/v1/admin/audit-events/statistics",
            headers=superadmin_headers,
            params=params
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "data" in data
        assert "summary" in data["data"]
        assert "breakdown" in data["data"]
        
        # Summary should have total counts
        summary = data["data"]["summary"]
        assert "total_events" in summary
        assert "unique_users" in summary
        assert "unique_resources" in summary
        
        # Breakdown should be grouped by action
        breakdown = data["data"]["breakdown"]
        assert isinstance(breakdown, list)
        if breakdown:
            assert "action" in breakdown[0]
            assert "count" in breakdown[0]