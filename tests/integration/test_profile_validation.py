"""Integration tests for profile validation errors.

Tests input validation following quickstart error scenarios.
"""
import pytest
from httpx import AsyncClient


class TestProfileValidation:
    """Integration tests for profile field validation."""

    @pytest.mark.asyncio
    async def test_invalid_phone_number(
        self, client: AsyncClient, auth_headers: dict, test_user_id: str
    ):
        """T015: Invalid phone number returns 422 (Quickstart Scenario 10).
        
        Expected: FAIL (validation not implemented)
        """
        response = await client.put(
            f"/api/v1/users/{test_user_id}/profile",
            json={"phone": "abc123"},
            headers=auth_headers
        )
        
        assert response.status_code == 422
        
        error_data = response.json()
        assert "detail" in error_data
        # Should mention phone validation
        assert any("phone" in str(err).lower() for err in error_data["detail"])

    @pytest.mark.asyncio
    async def test_phone_too_short(
        self, client: AsyncClient, auth_headers: dict, test_user_id: str
    ):
        """T015: Phone number too short returns 422.
        
        Expected: FAIL (validation not implemented)
        """
        response = await client.put(
            f"/api/v1/users/{test_user_id}/profile",
            json={"phone": "123"},
            headers=auth_headers
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_phone_too_long(
        self, client: AsyncClient, auth_headers: dict, test_user_id: str
    ):
        """T015: Phone number too long returns 422.
        
        Expected: FAIL (validation not implemented)
        """
        response = await client.put(
            f"/api/v1/users/{test_user_id}/profile",
            json={"phone": "1234567890123456789012345"},
            headers=auth_headers
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_address_too_long(
        self, client: AsyncClient, auth_headers: dict, test_user_id: str
    ):
        """T015: Address exceeding 500 chars returns 422 (Quickstart Scenario 11).
        
        Expected: FAIL (validation not implemented)
        """
        long_address = "x" * 501
        
        response = await client.put(
            f"/api/v1/users/{test_user_id}/profile",
            json={"address": long_address},
            headers=auth_headers
        )
        
        assert response.status_code == 422
        
        error_data = response.json()
        assert "detail" in error_data
        # Should mention address validation
        assert any("address" in str(err).lower() for err in error_data["detail"])

    @pytest.mark.asyncio
    async def test_full_name_too_long(
        self, client: AsyncClient, auth_headers: dict, test_user_id: str
    ):
        """T015: Full name exceeding 100 chars returns 422.
        
        Expected: FAIL (validation not implemented)
        """
        long_name = "x" * 101
        
        response = await client.put(
            f"/api/v1/users/{test_user_id}/profile",
            json={"full_name": long_name},
            headers=auth_headers
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_string_converted_to_null(
        self, client: AsyncClient, auth_headers: dict, test_user_id: str
    ):
        """T015: Empty strings should be converted to null.
        
        Expected: FAIL (normalization not implemented)
        """
        response = await client.put(
            f"/api/v1/users/{test_user_id}/profile",
            json={"full_name": "Test User", "phone": "", "address": ""},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["full_name"] == "Test User"
        assert data["phone"] is None
        assert data["address"] is None

    @pytest.mark.asyncio
    async def test_valid_profile_data(
        self, client: AsyncClient, auth_headers: dict, test_user_id: str
    ):
        """T015: Valid profile data should succeed.
        
        Expected: FAIL (endpoint not implemented)
        """
        valid_data = {
            "full_name": "Valid User Name",
            "phone": "+1-555-1234567",
            "address": "123 Main St\nApt 4\nCity, State 12345"
        }
        
        response = await client.put(
            f"/api/v1/users/{test_user_id}/profile",
            json=valid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["full_name"] == "Valid User Name"
        assert data["phone"] == "+1-555-1234567"
        assert data["address"] == "123 Main St\nApt 4\nCity, State 12345"
