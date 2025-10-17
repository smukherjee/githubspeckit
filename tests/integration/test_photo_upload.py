"""Integration tests for photo upload functionality.

Tests photo upload, processing, and storage following quickstart scenarios.
"""
import pytest
from httpx import AsyncClient
import io
from PIL import Image


class TestPhotoUpload:
    """Integration tests for profile photo upload."""

    @pytest.mark.asyncio
    async def test_upload_profile_photo(
        self, client: AsyncClient, auth_headers: dict, test_user_id: str
    ):
        """T012: User uploads profile photo (Quickstart Scenario 4).
        
        Expected: FAIL (photo processor not implemented)
        
        Verifies:
        - 202 status (async processing)
        - 3 variants generated (640x640, 96x96, 48x48)
        - URLs updated in profile
        - Processing completes <5s
        """
        import time
        
        # Create a 1000x1000 test JPEG (~5MB simulated)
        img = Image.new('RGB', (1000, 1000), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=95)
        img_bytes.seek(0)
        
        files = {"photo": ("profile.jpg", img_bytes, "image/jpeg")}
        
        start_time = time.time()
        
        # Upload photo
        upload_response = await client.post(
            f"/api/v1/users/{test_user_id}/profile/photo",
            files=files,
            headers=auth_headers
        )
        
        assert upload_response.status_code == 202, "Expected 202 Accepted"
        
        upload_data = upload_response.json()
        assert upload_data["status"] == "processing"
        assert "message" in upload_data
        
        # Wait for background processing (max 5s)
        import asyncio
        await asyncio.sleep(1)  # Give background task time to complete
        
        # Verify profile updated with photo URLs
        profile_response = await client.get(
            f"/api/v1/users/{test_user_id}/profile",
            headers=auth_headers
        )
        
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        
        # All 3 photo URLs should be set
        assert profile_data["photo_display_url"] is not None
        assert profile_data["photo_thumbnail_url"] is not None
        assert profile_data["photo_avatar_url"] is not None
        
        # URLs should contain user_id
        assert test_user_id in profile_data["photo_display_url"]
        assert test_user_id in profile_data["photo_thumbnail_url"]
        assert test_user_id in profile_data["photo_avatar_url"]
        
        # Verify processing time
        elapsed = time.time() - start_time
        assert elapsed < 5.0, f"Photo processing took {elapsed}s (expected <5s)"

    @pytest.mark.asyncio
    async def test_replace_existing_photo(
        self, client: AsyncClient, auth_headers: dict, test_user_id: str
    ):
        """T012: User replaces existing photo (Quickstart Scenario 5).
        
        Expected: FAIL (photo replacement not implemented)
        """
        # Upload first photo
        img1 = Image.new('RGB', (500, 500), color='red')
        img1_bytes = io.BytesIO()
        img1.save(img1_bytes, format='JPEG')
        img1_bytes.seek(0)
        
        await client.post(
            f"/api/v1/users/{test_user_id}/profile/photo",
            files={"photo": ("photo1.jpg", img1_bytes, "image/jpeg")},
            headers=auth_headers
        )
        
        # Get initial photo URLs
        profile1 = await client.get(f"/api/v1/users/{test_user_id}/profile", headers=auth_headers)
        old_urls = profile1.json()
        
        # Upload second photo
        img2 = Image.new('RGB', (500, 500), color='green')
        img2_bytes = io.BytesIO()
        img2.save(img2_bytes, format='JPEG')
        img2_bytes.seek(0)
        
        await client.post(
            f"/api/v1/users/{test_user_id}/profile/photo",
            files={"photo": ("photo2.jpg", img2_bytes, "image/jpeg")},
            headers=auth_headers
        )
        
        import asyncio
        await asyncio.sleep(1)
        
        # Get updated photo URLs
        profile2 = await client.get(f"/api/v1/users/{test_user_id}/profile", headers=auth_headers)
        new_urls = profile2.json()
        
        # URLs should be different (old photos replaced)
        assert new_urls["photo_display_url"] != old_urls["photo_display_url"]
        assert new_urls["photo_thumbnail_url"] != old_urls["photo_thumbnail_url"]
        assert new_urls["photo_avatar_url"] != old_urls["photo_avatar_url"]

    @pytest.mark.asyncio
    async def test_delete_profile_photo(
        self, client: AsyncClient, auth_headers: dict, test_user_id: str
    ):
        """T012: User removes profile photo (Quickstart Scenario 6).
        
        Expected: FAIL (photo deletion not implemented)
        """
        # Upload photo first
        img = Image.new('RGB', (500, 500), color='yellow')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        await client.post(
            f"/api/v1/users/{test_user_id}/profile/photo",
            files={"file": ("photo.jpg", img_bytes, "image/jpeg")},
            headers=auth_headers
        )
        
        import asyncio
        await asyncio.sleep(1)
        
        # Delete photo
        delete_response = await client.delete(
            f"/api/v1/users/{test_user_id}/profile/photo",
            headers=auth_headers
        )
        
        assert delete_response.status_code == 204
        
        # Verify photo URLs set to null
        profile_response = await client.get(
            f"/api/v1/users/{test_user_id}/profile",
            headers=auth_headers
        )
        
        profile_data = profile_response.json()
        assert profile_data["photo_display_url"] is None
        assert profile_data["photo_thumbnail_url"] is None
        assert profile_data["photo_avatar_url"] is None
