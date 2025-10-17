"""Integration tests for profile management workflows.

Tests user profile creation and updates following quickstart scenarios.
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestProfileManagement:
    """Integration tests for profile CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_profile_with_full_details(
        self, client: AsyncClient, auth_headers: dict, test_user_id: str
    ):
        """T010: User creates profile with full details (Quickstart Scenario 1).
        
        Expected: FAIL (profile service not implemented)
        """
        profile_data = {
            "full_name": "Alice Johnson",
            "phone": "+1-555-987-6543",
            "address": "456 Oak Ave\nApt 2C\nBoston, MA 02101"
        }
        
        # Create profile
        create_response = await client.put(
            f"/api/v1/users/{test_user_id}/profile",
            json=profile_data,
            headers=auth_headers
        )
        
        assert create_response.status_code == 200
        created_data = create_response.json()
        assert created_data["full_name"] == "Alice Johnson"
        assert created_data["phone"] == "+1-555-987-6543"
        assert created_data["address"] == "456 Oak Ave\nApt 2C\nBoston, MA 02101"
        assert created_data["user_id"] == test_user_id
        
        # Retrieve profile
        get_response = await client.get(
            f"/api/v1/users/{test_user_id}/profile",
            headers=auth_headers
        )
        
        assert get_response.status_code == 200
        retrieved_data = get_response.json()
        assert retrieved_data["full_name"] == "Alice Johnson"
        assert retrieved_data["phone"] == "+1-555-987-6543"

    @pytest.mark.asyncio
    async def test_update_profile_partial(
        self, client: AsyncClient, auth_headers: dict, test_user_id: str
    ):
        """T011: User updates only phone field (Quickstart Scenario 2).
        
        Expected: FAIL (update logic not implemented)
        """
        # Create initial profile
        initial_data = {
            "full_name": "Bob Williams",
            "phone": "+1-555-111-2222",
            "address": "789 Pine St"
        }
        await client.put(
            f"/api/v1/users/{test_user_id}/profile",
            json=initial_data,
            headers=auth_headers
        )
        
        # Update only phone
        update_data = {"phone": "+1-555-999-8888"}
        update_response = await client.put(
            f"/api/v1/users/{test_user_id}/profile",
            json=update_data,
            headers=auth_headers
        )
        
        assert update_response.status_code == 200
        updated_data = update_response.json()
        
        # Phone updated
        assert updated_data["phone"] == "+1-555-999-8888"
        
        # Other fields unchanged
        assert updated_data["full_name"] == "Bob Williams"
        assert updated_data["address"] == "789 Pine St"

    @pytest.mark.asyncio
    async def test_clear_optional_fields(
        self, client: AsyncClient, auth_headers: dict, test_user_id: str
    ):
        """T011: User clears phone and address fields (Quickstart Scenario 3).
        
        Expected: FAIL (null handling not implemented)
        """
        # Create profile with all fields
        await client.put(
            f"/api/v1/users/{test_user_id}/profile",
            json={"full_name": "Charlie Brown", "phone": "+1-555-333-4444", "address": "123 Maple Dr"},
            headers=auth_headers
        )
        
        # Clear phone and address
        update_response = await client.put(
            f"/api/v1/users/{test_user_id}/profile",
            json={"phone": None, "address": None},
            headers=auth_headers
        )
        
        assert update_response.status_code == 200
        data = update_response.json()
        
        assert data["full_name"] == "Charlie Brown"
        assert data["phone"] is None
        assert data["address"] is None
