"""
Authentication Flow Integration Tests

Tests the complete authentication lifecycle:
- User login with credentials
- JWT token validation
- Token usage for authenticated endpoints
- Token expiration handling
- Invalid credentials rejection
"""
import pytest
from httpx import AsyncClient


class TestAuthenticationFlow:
    """Test authentication endpoints and token lifecycle."""
    
    @pytest.mark.asyncio
    async def test_successful_login(self, api_client: AsyncClient):
        """Test successful login with valid credentials."""
        response = await api_client.post(
            "/api/v1/auth/login",
            json={
                "email": "infysightsa@infysight.com",
                "password": "infysightsa123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0
    
    @pytest.mark.asyncio
    async def test_login_with_invalid_password(self, api_client: AsyncClient):
        """Test login fails with incorrect password."""
        response = await api_client.post(
            "/api/v1/auth/login",
            json={
                "email": "infysightsa@infysight.com",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_login_with_nonexistent_user(self, api_client: AsyncClient):
        """Test login fails for non-existent user."""
        response = await api_client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "anypassword"
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_login_with_invalid_email_format(self, api_client: AsyncClient):
        """Test login validation rejects invalid email format."""
        response = await api_client.post(
            "/api/v1/auth/login",
            json={
                "email": "not-an-email",
                "password": "anypassword"
            }
        )
        
        # Should fail validation (422) or authentication (401)
        assert response.status_code in [401, 422]
    
    @pytest.mark.asyncio
    async def test_token_usage_in_authenticated_endpoint(
        self, 
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Test using JWT token to access protected endpoint."""
        # Try accessing users endpoint (requires authentication)
        response = await api_client.get(
            "/api/v1/users",
            headers=auth_headers
        )
        
        # Should succeed with valid token
        assert response.status_code == 200
        data = response.json()
        # Response should be structured with "users" key
        assert "users" in data
        assert isinstance(data["users"], list)
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, api_client: AsyncClient):
        """Test protected endpoint rejects request without token."""
        response = await api_client.get("/api/v1/users")
        
        # Should require authentication
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_with_invalid_token(self, api_client: AsyncClient):
        """Test protected endpoint rejects invalid token."""
        response = await api_client.get(
            "/api/v1/users",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        
        # Should reject invalid token
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_with_malformed_auth_header(
        self, 
        api_client: AsyncClient
    ):
        """Test protected endpoint rejects malformed authorization header."""
        # Missing 'Bearer' prefix
        response = await api_client.get(
            "/api/v1/users",
            headers={"Authorization": "some_token"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_login_case_insensitive_email(self, api_client: AsyncClient):
        """Test login works with different email casing."""
        # Try uppercase version of email
        response = await api_client.post(
            "/api/v1/auth/login",
            json={
                "email": "INFYSIGHTSA@INFYSIGHT.COM",
                "password": "infysightsa123"
            }
        )
        
        # Should succeed (emails are case-insensitive)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    @pytest.mark.asyncio
    async def test_login_password_is_case_sensitive(self, api_client: AsyncClient):
        """Test password verification is case-sensitive."""
        response = await api_client.post(
            "/api/v1/auth/login",
            json={
                "email": "infysightsa@infysight.com",
                "password": "INFYSIGHTSA123"  # Wrong case
            }
        )
        
        # Should fail (passwords are case-sensitive)
        assert response.status_code == 401


class TestTokenRevocation:
    """Test token revocation functionality."""
    
    @pytest.mark.asyncio
    async def test_revoke_token_endpoint_exists(
        self,
        api_client: AsyncClient,
        auth_headers: dict
    ):
        """Test token revocation endpoint is accessible."""
        response = await api_client.post(
            "/api/v1/auth/revoke",
            headers=auth_headers
        )
        
        # Should be 200 (success) or 501 (not implemented stub)
        assert response.status_code in [200, 501]
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Token revocation is stub - FR-033 implementation pending")
    async def test_revoked_token_cannot_access_protected_endpoint(
        self,
        api_client: AsyncClient
    ):
        """Test revoked token cannot access protected endpoints."""
        # Login to get token
        login_response = await api_client.post(
            "/api/v1/auth/login",
            json={
                "email": "infysightsa@infysight.com",
                "password": "infysightsa123"
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Revoke the token
        revoke_response = await api_client.post(
            "/api/v1/auth/revoke",
            headers=headers
        )
        assert revoke_response.status_code == 200
        
        # Try to use revoked token
        protected_response = await api_client.get(
            "/api/v1/users",
            headers=headers
        )
        
        # Should be rejected
        assert protected_response.status_code == 401
