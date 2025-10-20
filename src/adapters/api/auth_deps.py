"""Authentication dependencies for FastAPI endpoints.

Provides JWT token validation and user authentication for protected endpoints.
"""
from typing import Annotated, Any, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.api.deps import get_db_session, get_jwt_service
from adapters.persistence.repositories import SQLAlchemyUserRepository
from domain.users.models import User, UserStatus


security = HTTPBearer(auto_error=False)


class AuthenticatedUser:
    """Authenticated user context from JWT token."""
    
    def __init__(
        self,
        user_id: str,
        tenant_id: str,
        roles: List[str],
        email: str,
        status: UserStatus
    ):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.roles = roles
        self.email = email
        self.status = status
    
    def has_role(self, role: str) -> bool:
        """Check if user has specific role."""
        return role in self.roles
    
    def is_superadmin(self) -> bool:
        """Check if user is superadmin."""
        return "superadmin" in self.roles


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    jwt_service: Annotated[Any, Depends(get_jwt_service)]
) -> AuthenticatedUser:
    """
    Validate JWT token and return authenticated user.
    
    Raises:
        HTTPException: 401 if token is missing, invalid, or user not found
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    try:
        # Decode and validate JWT token
        claims = jwt_service.decode(token)
        
        # Extract user information from claims
        user_id = claims.get("sub")
        tenant_id = claims.get("tenant_id")
        roles = claims.get("roles", [])
        
        if not user_id or not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify user still exists and is active
        user_repo = SQLAlchemyUserRepository(session)
        user = await user_repo.get(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if user.status != UserStatus.active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is not active",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return AuthenticatedUser(
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            roles=user.roles,
            email=user.email,
            status=user.status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Invalid token format, signature, or expired
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_superadmin(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)]
) -> AuthenticatedUser:
    """
    Require superadmin role.
    
    Raises:
        HTTPException: 403 if user is not superadmin
    """
    if not current_user.is_superadmin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required"
        )
    return current_user


# Type aliases for dependency injection
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
CurrentSuperadmin = Annotated[AuthenticatedUser, Depends(get_current_superadmin)]


__all__ = [
    "AuthenticatedUser",
    "get_current_user",
    "get_current_superadmin",
    "CurrentUser",
    "CurrentSuperadmin",
]
