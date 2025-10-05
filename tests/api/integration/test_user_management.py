"""
User Management Integration Tests

Tests user lifecycle operations:
- List users
- Create new user
- Disable user
- Restore user
- Update user roles
- RBAC enforcement
"""
import pytest
from httpx import AsyncClient
import uuid


class TestUserLifecycle:
    """Test user CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_list_users(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Test listing all users."""
        response = await api_client.get(
            "/api/v1/users",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Handle both list and dict formats
        if isinstance(data, dict) and "users" in data:
            users = data["users"]
        else:
            users = data
        assert isinstance(users, list)
        assert len(users) >= 1  # At least infysightsa user
        
        # Verify infysightsa user exists
        user_emails = [u["email"] for u in users]
        assert "infysightsa@infysight.com" in user_emails
    
    @pytest.mark.asyncio
    async def test_create_user(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        seeded_database: dict
    ):
        """Test creating a new user."""
        tenant_id = seeded_database["tenant_id"]
        email = f"test_user_{uuid.uuid4().hex[:8]}@infysight.com"
        
        response = await api_client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "tenant_id": tenant_id,
                "email": email,
                "password": "TestPassword123!",
                "roles": ["user"]
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert data["email"] == email
        assert "user_id" in data
        assert data["status"] == "active"
        assert data["roles"] == ["user"]
        assert "password" not in data  # Password should not be returned
        assert "password_hash" not in data
        assert "created_at" in data
        assert "updated_at" in data
    
    @pytest.mark.asyncio
    async def test_create_duplicate_user_fails(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        seeded_database: dict
    ):
        """Test creating user with duplicate email fails."""
        # Try to create user with existing email
        response = await api_client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "tenant_id": seeded_database["tenant_id"],
                "email": "infysightsa@infysight.com",
                "password": "TestPassword123!",
                "roles": ["user"]
            }
        )
        
        # Should fail with 409 Conflict
        assert response.status_code == 409
    
    @pytest.mark.asyncio
    async def test_disable_user(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        seeded_database: dict
    ):
        """Test disabling a user."""
        # Create user first
        email = f"test_user_{uuid.uuid4().hex[:8]}@infysight.com"
        create_response = await api_client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "tenant_id": seeded_database["tenant_id"],
                "email": email,
                "password": "TestPassword123!",
                "roles": ["user"]
            }
        )
        assert create_response.status_code == 201
        user_id = create_response.json()["user_id"]
        
        # Disable user
        disable_response = await api_client.delete(
            f"/api/v1/users/{user_id}",
            headers=auth_headers
        )
        
        assert disable_response.status_code == 204
        
        # Verify user is disabled (should still appear in list but with different status)
        list_response = await api_client.get(
            "/api/v1/users",
            headers=auth_headers
        )
        assert list_response.status_code == 200
        users_data = list_response.json()
        users = users_data.get("users", users_data) if isinstance(users_data, dict) else users_data
        disabled_user = next((u for u in users if u["user_id"] == user_id), None)
        
        # User might be filtered out or have disabled status
        if disabled_user:
            assert disabled_user["status"] == "disabled"
    
    @pytest.mark.asyncio
    async def test_restore_user(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        seeded_database: dict
    ):
        """Test restoring a disabled user."""
        # Create and disable user
        email = f"test_user_{uuid.uuid4().hex[:8]}@infysight.com"
        create_response = await api_client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "tenant_id": seeded_database["tenant_id"],
                "email": email,
                "password": "TestPassword123!",
                "roles": ["user"]
            }
        )
        assert create_response.status_code == 201
        user_id = create_response.json()["user_id"]
        
        disable_response = await api_client.delete(
            f"/api/v1/users/{user_id}",
            headers=auth_headers
        )
        assert disable_response.status_code == 204
        
        # Restore user
        restore_response = await api_client.post(
            f"/api/v1/users/{user_id}/restore",
            headers=auth_headers
        )
        
        assert restore_response.status_code == 200
        
        # Verify user is restored
        list_response = await api_client.get(
            "/api/v1/users",
            headers=auth_headers
        )
        assert list_response.status_code == 200
        users_data = list_response.json()
        users = users_data.get("users", users_data) if isinstance(users_data, dict) else users_data
        restored_user = next((u for u in users if u["user_id"] == user_id), None)
        assert restored_user is not None
        assert restored_user["status"] == "active"


class TestUserAccessControl:
    """Test RBAC enforcement for user operations."""
    
    @pytest.mark.asyncio
    async def test_list_users_requires_authentication(
        self,
        api_client: AsyncClient
    ):
        """Test listing users requires authentication."""
        response = await api_client.get("/api/v1/users")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_create_user_requires_authentication(
        self,
        api_client: AsyncClient
    ):
        """Test creating user requires authentication."""
        response = await api_client.post(
            "/api/v1/users",
            json={
                "tenant_id": str(uuid.uuid4()),
                "email": "test@example.com",
                "password": "TestPassword123!",
                "roles": ["user"]
            }
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_disabled_user_cannot_login(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        seeded_database: dict
    ):
        """Test disabled user cannot authenticate."""
        # Create user
        email = f"test_user_{uuid.uuid4().hex[:8]}@infysight.com"
        password = "TestPassword123!"
        
        create_response = await api_client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "tenant_id": seeded_database["tenant_id"],
                "email": email,
                "password": password,
                "roles": ["user"]
            }
        )
        assert create_response.status_code == 201
        user_id = create_response.json()["user_id"]
        
        # Verify user can login initially
        login1_response = await api_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        assert login1_response.status_code == 200
        
        # Disable user
        disable_response = await api_client.delete(
            f"/api/v1/users/{user_id}",
            headers=auth_headers
        )
        assert disable_response.status_code == 204
        
        # Verify user cannot login after being disabled
        login2_response = await api_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        assert login2_response.status_code == 401


class TestUserValidation:
    """Test user input validation."""
    
    @pytest.mark.asyncio
    async def test_create_user_with_invalid_email(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        seeded_database: dict
    ):
        """Test creating user with invalid email fails."""
        response = await api_client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "tenant_id": seeded_database["tenant_id"],
                "email": "not-an-email",
                "password": "TestPassword123!",
                "roles": ["user"]
            }
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_user_with_weak_password(
        self,
        api_client: AsyncClient,
        auth_headers: dict,
        seeded_database: dict
    ):
        """Test creating user with weak password fails."""
        response = await api_client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "tenant_id": seeded_database["tenant_id"],
                "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
                "password": "weak",
                "roles": ["user"]
            }
        )
        
        # Should fail validation
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_user_with_invalid_tenant_id(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Test creating user with non-existent tenant fails."""
        response = await api_client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "tenant_id": str(uuid.uuid4()),  # Non-existent tenant
                "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
                "password": "TestPassword123!",
                "roles": ["user"]
            }
        )
        
        # Should fail with 404 Not Found
        assert response.status_code == 404
