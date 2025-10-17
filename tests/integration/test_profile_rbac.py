"""Integration tests for RBAC enforcement on profile endpoints.

Tests tenant isolation and role-based access control.
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestProfileRBAC:
    """Integration tests for profile RBAC enforcement."""

    @pytest.mark.asyncio
    async def test_user_cannot_edit_other_profiles(
        self, client: AsyncClient, regular_user_headers: dict
    ):
        """T013: Regular user cannot edit another user's profile (Quickstart Scenario 7).
        
        Expected: FAIL (RBAC middleware not implemented)
        """
        other_user_id = str(uuid4())
        
        response = await client.put(
            f"/api/v1/users/{other_user_id}/profile",
            json={"full_name": "Unauthorized Edit"},
            headers=regular_user_headers
        )
        
        assert response.status_code == 403, "Expected 403 Forbidden"
        
        error_data = response.json()
        assert "detail" in error_data
        assert "permission" in error_data["detail"].lower() or "forbidden" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_user_can_view_own_profile(
        self, client: AsyncClient, regular_user_headers: dict, regular_user_id: str
    ):
        """T013: Regular user can view own profile.
        
        Expected: FAIL (RBAC not implemented)
        """
        # Create profile first
        await client.put(
            f"/api/v1/users/{regular_user_id}/profile",
            json={"full_name": "Regular User"},
            headers=regular_user_headers
        )
        
        response = await client.get(
            f"/api/v1/users/{regular_user_id}/profile",
            headers=regular_user_headers
        )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_user_can_edit_own_profile(
        self, client: AsyncClient, regular_user_headers: dict, regular_user_id: str
    ):
        """T013: Regular user can edit own profile.
        
        Expected: FAIL (RBAC not implemented)
        """
        response = await client.put(
            f"/api/v1/users/{regular_user_id}/profile",
            json={"full_name": "My Updated Name"},
            headers=regular_user_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "My Updated Name"

    @pytest.mark.asyncio
    async def test_tenant_admin_can_view_tenant_user_profiles(
        self, client: AsyncClient, tenant_admin_headers: dict, same_tenant_user_id: str
    ):
        """T014: Tenant admin can view profiles in same tenant (Quickstart Scenario 8).
        
        Expected: FAIL (tenant isolation logic not implemented)
        """
        # Create profile for same-tenant user
        # Note: We need headers for same_tenant_user, but we'll use tenant_admin to create it
        # In real scenario, user would create their own profile
        await client.put(
            f"/api/v1/users/{same_tenant_user_id}/profile",
            json={"full_name": "Same Tenant User"},
            headers=tenant_admin_headers
        )
        
        response = await client.get(
            f"/api/v1/users/{same_tenant_user_id}/profile",
            headers=tenant_admin_headers
        )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_tenant_admin_cannot_view_other_tenant_profiles(
        self, client: AsyncClient, tenant_admin_headers: dict
    ):
        """T014: Tenant admin cannot view profiles in different tenant.
        
        Expected: FAIL (tenant isolation not implemented)
        """
        other_tenant_user_id = str(uuid4())
        
        response = await client.get(
            f"/api/v1/users/{other_tenant_user_id}/profile",
            headers=tenant_admin_headers
        )
        
        assert response.status_code == 403, "Expected 403 Forbidden for cross-tenant access"

    @pytest.mark.asyncio
    async def test_superadmin_can_view_all_profiles(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        """T014: Superadmin can view any user's profile (Quickstart Scenario 9).
        
        Expected: FAIL (superadmin logic not implemented)
        """
        any_user_id = str(uuid4())
        
        response = await client.get(
            f"/api/v1/users/{any_user_id}/profile",
            headers=superadmin_headers
        )
        
        # Superadmin should get 200 or 404 (if profile doesn't exist), not 403
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_user_cannot_upload_photo_for_others(
        self, client: AsyncClient, regular_user_headers: dict, regular_user_id: str
    ):
        """T013: User cannot upload photo for another user.
        
        Expected: FAIL (RBAC not implemented)
        """
        import io
        from PIL import Image
        
        other_user_id = str(uuid4())
        
        # Create profile for other user (as superadmin would)
        # This simulates another user's existing profile
        
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        response = await client.post(
            f"/api/v1/users/{other_user_id}/profile/photo",
            files={"photo": ("test.jpg", img_bytes, "image/jpeg")},
            headers=regular_user_headers
        )
        
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}: {response.text}"