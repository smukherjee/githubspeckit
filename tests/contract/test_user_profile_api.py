"""Contract tests for User Profile API endpoints.

These tests validate API contracts match OpenAPI specification:
specs/003-user-profile-details/contracts/openapi-user-profile.yaml

Tests MUST FAIL initially (endpoints not implemented yet).
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestUserProfileContracts:
    """Contract tests for /api/v1/users/{user_id}/profile endpoints."""

    @pytest.mark.asyncio
    async def test_get_profile_contract(self, client: AsyncClient, auth_headers: dict, test_user_id: str):
        """T006: GET /api/v1/users/{user_id}/profile returns UserProfileResponse schema.
        
        Creates a profile for test user and verifies GET returns correct schema.
        """
        # First create a profile for the test user
        create_response = await client.put(
            f"/api/v1/users/{test_user_id}/profile",
            json={
                "full_name": "Test User",
                "phone": "+1234567890",
                "address": "123 Test St"
            },
            headers=auth_headers
        )
        assert create_response.status_code == 200, f"Failed to create profile: {create_response.text}"
        
        # Now test GET endpoint
        response = await client.get(
            f"/api/v1/users/{test_user_id}/profile",
            headers=auth_headers
        )
        
        # Contract assertions
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "user_id" in data
        assert "full_name" in data
        assert "phone" in data
        assert "address" in data
        assert "photo_display_url" in data
        assert "photo_thumbnail_url" in data
        assert "photo_avatar_url" in data
        assert "created_at" in data
        assert "updated_at" in data
        
        # Validate types
        assert isinstance(data["user_id"], str)
        assert data["full_name"] is None or isinstance(data["full_name"], str)
        assert data["phone"] is None or isinstance(data["phone"], str)
        assert data["address"] is None or isinstance(data["address"], str)

    @pytest.mark.asyncio
    async def test_put_profile_contract(self, client: AsyncClient, auth_headers: dict, test_user_id: str):
        """T007: PUT /api/v1/users/{user_id}/profile validates UserProfileUpdateRequest.
        
        Tests creating/updating a profile with valid data.
        """
        profile_data = {
            "full_name": "John Smith",
            "phone": "+1-555-123-4567",
            "address": "123 Main St"
        }
        
        response = await client.put(
            f"/api/v1/users/{test_user_id}/profile",
            json=profile_data,
            headers=auth_headers
        )
        
        # Contract assertions
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["full_name"] == "John Smith"
        assert data["phone"] == "+1-555-123-4567"
        assert data["address"] == "123 Main St"

    @pytest.mark.asyncio
    async def test_put_profile_validation_errors(self, client: AsyncClient, auth_headers: dict):
        """T007: PUT validates field constraints (full_name max 100, phone 7-20 chars).
        
        Expected: FAIL (validation not implemented)
        """
        user_id = str(uuid4())
        
        # Test full_name too long
        response = await client.put(
            f"/api/v1/users/{user_id}/profile",
            json={"full_name": "x" * 101},
            headers=auth_headers
        )
        assert response.status_code == 422, "Expected 422 Unprocessable Entity for full_name > 100"
        
        # Test phone too short
        response = await client.put(
            f"/api/v1/users/{user_id}/profile",
            json={"phone": "123"},
            headers=auth_headers
        )
        assert response.status_code == 422, "Expected 422 for phone < 7 chars"
        
        # Test address too long
        response = await client.put(
            f"/api/v1/users/{user_id}/profile",
            json={"address": "x" * 501},
            headers=auth_headers
        )
        assert response.status_code == 422, "Expected 422 for address > 500"

    @pytest.mark.asyncio
    async def test_post_photo_contract(self, client: AsyncClient, auth_headers: dict, test_user_id: str):
        """T008: POST /api/v1/users/{user_id}/profile/photo accepts photo upload.
        
        Tests photo upload endpoint returns 202 Accepted.
        """
        # First create a profile
        await client.put(
            f"/api/v1/users/{test_user_id}/profile",
            json={"full_name": "Test User"},
            headers=auth_headers
        )
        
        # Create a small test JPEG (1x1 pixel)
        import io
        from PIL import Image
        
        img = Image.new('RGB', (1, 1), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        files = {"photo": ("test.jpg", img_bytes, "image/jpeg")}
        
        response = await client.post(
            f"/api/v1/users/{test_user_id}/profile/photo",
            files=files,
            headers=auth_headers
        )
        
        # Contract assertions
        assert response.status_code == 202, f"Expected 202 Accepted, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "processing"
        assert "message" in data

    @pytest.mark.asyncio
    async def test_post_photo_invalid_file(self, client: AsyncClient, auth_headers: dict, test_user_id: str):
        """T008: POST photo rejects invalid file types.
        
        Tests that non-image files are rejected with 400.
        """
        # First create a profile
        await client.put(
            f"/api/v1/users/{test_user_id}/profile",
            json={"full_name": "Test User"},
            headers=auth_headers
        )
        
        # Upload text file instead of image
        files = {"photo": ("test.txt", b"not an image", "text/plain")}
        
        response = await client.post(
            f"/api/v1/users/{test_user_id}/profile/photo",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == 400, f"Expected 400 Bad Request, got {response.status_code}: {response.text}"

    @pytest.mark.asyncio
    async def test_post_photo_file_too_large(self, client: AsyncClient, auth_headers: dict, test_user_id: str):
        """T008: POST photo rejects files exceeding size limit.
        
        Tests that files >10MB are rejected with 413.
        """
        # First create a profile
        await client.put(
            f"/api/v1/users/{test_user_id}/profile",
            json={"full_name": "Test User"},
            headers=auth_headers
        )
        
        # Create 11MB file (exceeds 10MB limit)
        large_file = b"x" * (11 * 1024 * 1024)
        files = {"photo": ("large.jpg", large_file, "image/jpeg")}
        
        response = await client.post(
            f"/api/v1/users/{test_user_id}/profile/photo",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == 413, f"Expected 413 Payload Too Large, got {response.status_code}: {response.text}"

    @pytest.mark.asyncio
    async def test_delete_photo_contract(self, client: AsyncClient, auth_headers: dict, test_user_id: str):
        """T009: DELETE /api/v1/users/{user_id}/profile/photo returns 204 No Content.
        
        Tests deleting profile photo (sets URLs to null).
        """
        # First create a profile (photos would be added via POST in real scenario)
        await client.put(
            f"/api/v1/users/{test_user_id}/profile",
            json={"full_name": "Test User"},
            headers=auth_headers
        )
        
        response = await client.delete(
            f"/api/v1/users/{test_user_id}/profile/photo",
            headers=auth_headers
        )
        
        # Contract assertions
        assert response.status_code == 204, f"Expected 204 No Content, got {response.status_code}: {response.text}"
        assert response.content == b"", "Expected empty response body"

    @pytest.mark.asyncio
    async def test_get_profile_rbac_forbidden(self, client: AsyncClient, regular_user_headers: dict):
        """T006: GET profile enforces RBAC (403 for cross-tenant access).
        
        Expected: FAIL (RBAC not implemented)
        """
        other_tenant_user_id = str(uuid4())
        
        response = await client.get(
            f"/api/v1/users/{other_tenant_user_id}/profile",
            headers=regular_user_headers
        )
        
        assert response.status_code == 403, "Expected 403 Forbidden for cross-tenant access"
