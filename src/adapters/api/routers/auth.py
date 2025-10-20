from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, EmailStr
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
import redis.asyncio as redis

from auth_core.hashers import default_hasher
from adapters.api.deps import get_audit_service, get_db_session, get_redis_client
from domain.users.models import UserStatus
from adapters.api.deps import get_user_repo, get_auth_service, get_jwt_service
from adapters.persistence.repositories import SQLAlchemyUserRepository
from adapters.persistence.replay_store import DatabaseReplayStore

router = APIRouter(prefix="/v1/auth", tags=["auth"])

_AuthServiceDep = get_auth_service
_JWTDep = get_jwt_service


class LoginRequest(BaseModel):
    email: EmailStr  # Changed from user_id to email
    password: str
    mfa_code: Optional[str] = None


class UserInfo(BaseModel):
    """User information returned in login response"""
    user_id: str
    email: str
    tenant_id: str
    roles: list[str]
    status: str
    model_config = ConfigDict()


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Token lifetime in seconds
    user: UserInfo  # Current user object
    model_config = ConfigDict()


class RevokeRequest(BaseModel):
    user_id: str


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_service: Any = Depends(_AuthServiceDep),
    jwt_service: Any = Depends(_JWTDep),
    audit: Any = Depends(get_audit_service)
) -> LoginResponse:
    """
    Authenticate user with email and password.
    
    Changed from user_id to email for standard login flow (Phase 3 API-database integration).
    """
    # Get user repository with database session
    user_repo = SQLAlchemyUserRepository(session)
    
    # Look up user by email (case-insensitive)
    user = await user_repo.get_by_email(payload.email)
    if not user or not user.password_hash or user.status != UserStatus.active:
        # Log failed login attempt
        try:
            await audit.log(
                action_type="auth.login.failed",
                tenant_id=user.tenant_id if user else None,
                metadata={
                    "email": payload.email,
                    "reason": "user_not_found_or_inactive"
                }
            )
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="invalid_credentials")
    
    try:
        result = await auth_service.login_password(
            user_id=user.user_id,
            stored_hash=user.password_hash,
            password=payload.password,
            mfa_code=payload.mfa_code
        )
    except Exception:
        # Log failed login attempt
        try:
            await audit.log(
                action_type="auth.login.failed",
                tenant_id=user.tenant_id,
                metadata={
                    "user_id": user.user_id,
                    "email": user.email,
                    "reason": "invalid_password_or_mfa"
                }
            )
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="invalid_credentials")
    
    token = jwt_service.issue(sub=user.user_id, tenant_id=user.tenant_id, roles=user.roles)
    
    # Hash upgrade path (FR-051)
    if result.get("needs_rehash"):
        user.password_hash = default_hasher.hash(payload.password)
        # Emit audit event (FR-051 C-033)
        try:
            await audit.log(
                action_type="auth.password.hash_upgraded",
                tenant_id=user.tenant_id,
                metadata={"user_id": user.user_id}
            )
        except Exception:
            pass
        await user_repo.upsert(user)
    
    # Log successful login audit event
    try:
        await audit.log(
            action_type="auth.login.success",
            tenant_id=user.tenant_id,
            metadata={
                "user_id": user.user_id,
                "email": user.email,
                "login_method": "password"
            }
        )
    except Exception:
        # Don't fail login if audit logging fails
        pass
    
    # Create user info for response
    user_info = UserInfo(
        user_id=user.user_id,
        email=user.email,
        tenant_id=user.tenant_id,
        roles=user.roles,
        status=user.status.value  # Convert enum to string
    )
    
    # Token expires in 15 minutes (900 seconds)
    expires_in = 900
    
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=user_info
    )


@router.post("/revoke", status_code=200)
async def revoke(
    request: Request,
    authorization: str = Header(..., description="Bearer token to revoke"),
    session: AsyncSession = Depends(get_db_session),
    jwt_service: Any = Depends(_JWTDep),
    audit: Any = Depends(get_audit_service),
    redis_client: redis.Redis = Depends(get_redis_client)
) -> dict[str, str]:
    """Revoke authentication token (FR-033).
    
    Implements token replay detection by storing JWT ID (jti) in database.
    Clears any active Redis session for the user (tenant switching state).
    Subsequent use of the same token will be rejected by the authentication middleware.
    
    Args:
        request: FastAPI request (for session cookie access)
        authorization: Bearer token in format "Bearer <token>"
        session: Database session for replay store
        jwt_service: JWT service for token validation
        audit: Audit service for logging revocation event
        redis_client: Redis client for session clearing
    
    Returns:
        Success status with revoked jti
    
    Raises:
        HTTPException(401): If token is invalid or missing
        HTTPException(400): If authorization header format is wrong
    """
    # Extract token from Authorization header
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=400,
            detail="Invalid authorization header format. Expected: Bearer <token>"
        )
    
    token = authorization.split(" ", 1)[1]
    
    # Decode and validate token
    try:
        # Use jwt_service to decode token (will validate signature, expiration, etc.)
        payload = jwt_service.decode(token)
        jti = payload.get("jti")
        
        if not jti:
            raise HTTPException(
                status_code=401,
                detail="Token missing jti (JWT ID) claim"
            )
        
        # Calculate TTL from token expiration
        exp = payload.get("exp")
        if not exp:
            raise HTTPException(
                status_code=401,
                detail="Token missing exp (expiration) claim"
            )
        
        # TTL is time until token naturally expires
        now = datetime.now(timezone.utc)
        exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
        ttl_seconds = int((exp_dt - now).total_seconds())
        
        # Don't store expired tokens (no point)
        if ttl_seconds <= 0:
            raise HTTPException(
                status_code=401,
                detail="Token already expired"
            )
        
        # Store in replay detection database
        replay_store = DatabaseReplayStore(session)
        tenant_id = payload.get("tenant_id")
        
        # Register token as revoked (will prevent future use)
        await replay_store.register(
            jti=jti,
            ttl_seconds=ttl_seconds,
            tenant_id=tenant_id
        )
        
        # Commit the transaction
        await session.commit()
        
        # Clear Redis session if exists (tenant switching state)
        try:
            session_id = request.cookies.get("session_id")
            if session_id:
                redis_key = f"session:{session_id}:tenant_context"
                await redis_client.delete(redis_key)
        except Exception:
            # Don't fail revocation if Redis session clearing fails
            pass
        
        # Emit audit event for logout
        try:
            # Check if log method is async
            log_result = audit.log(
                action_type="auth.logout",
                tenant_id=tenant_id,
                metadata={
                    "jti": jti,
                    "user_id": payload.get("sub"),
                    "revoked_at": now.isoformat()
                }
            )
            # Await if it's a coroutine
            import inspect
            if inspect.iscoroutine(log_result):
                await log_result
        except Exception:
            # Don't fail revocation if audit logging fails
            pass
        
        return {
            "status": "revoked",
            "jti": jti,
            "message": "Token successfully revoked"
        }
        
    except JWTError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        # Rollback on any error
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Token revocation failed: {str(e)}"
        )
