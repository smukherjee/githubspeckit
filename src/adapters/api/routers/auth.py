from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, ConfigDict, EmailStr
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from auth_core.hashers import default_hasher
from adapters.api.deps import get_audit_service, get_db_session
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


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
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
        raise HTTPException(status_code=401, detail="invalid_credentials")
    
    try:
        result = await auth_service.login_password(
            user_id=user.user_id,
            stored_hash=user.password_hash,
            password=payload.password,
            mfa_code=payload.mfa_code
        )
    except Exception:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    
    token = jwt_service.issue(sub=user.user_id, tenant_id=user.tenant_id, roles=user.roles)
    
    # Hash upgrade path (FR-051)
    if result.get("needs_rehash"):
        user.password_hash = default_hasher.hash(payload.password)
        # Emit audit event (FR-051 C-033)
        try:
            audit.log(
                action_type="auth.password.hash_upgraded",
                tenant_id=user.tenant_id,
                metadata={"user_id": user.user_id}
            )
        except Exception:
            pass
        await user_repo.upsert(user)
    
    return LoginResponse(access_token=token, expires_at=datetime.now(timezone.utc) + timedelta(minutes=30))


@router.post("/revoke", status_code=200)
async def revoke(
    authorization: str = Header(..., description="Bearer token to revoke"),
    session: AsyncSession = Depends(get_db_session),
    jwt_service: Any = Depends(_JWTDep),
    audit: Any = Depends(get_audit_service)
) -> dict[str, str]:
    """Revoke authentication token (FR-033).
    
    Implements token replay detection by storing JWT ID (jti) in database.
    Subsequent use of the same token will be rejected by the authentication middleware.
    
    Args:
        authorization: Bearer token in format "Bearer <token>"
        session: Database session for replay store
        jwt_service: JWT service for token validation
        audit: Audit service for logging revocation event
    
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
        
        # Emit audit event for revocation
        try:
            # Check if log method is async
            log_result = audit.log(
                action_type="token.revoke",
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
