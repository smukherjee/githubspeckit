"""FastAPI dependency providers (Phase 3 database-backed DI).

Provides database session management and repository injection.
Uses SQLAlchemy async repositories with proper session lifecycle management.
"""
from functools import lru_cache
from typing import AsyncGenerator, Optional
from datetime import datetime
import os

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import redis.asyncio as redis

from adapters.persistence.db_config import DatabaseConfig
from adapters.persistence.repositories import (
    SQLAlchemyTenantRepository,
    SQLAlchemyUserRepository,
    SQLAlchemyPolicyRepository,
    SQLAlchemyFeatureFlagRepository,
    SQLAlchemyInvitationRepository,
    SQLAlchemyAuditAppender,
)
from domain.tenants.models import TenantRepository
from domain.users.models import UserRepository
from domain.policy.models import PolicyRepository
from domain.featureflags.models import FeatureFlagRepository
from domain.invitations.models import InvitationRepository
from services.user_lifecycle_service import UserLifecycleService
from services.invitations_service import InvitationService
from auth_core.registry import default_registry, AuthProviderRegistry
from auth_core.auth_service import AuthenticationService
from auth_core.jwt import JWTService, JWTKeySet


class AuditService:
    """Database-backed audit service (Phase 3).

    Appends audit events to database via SQLAlchemyAuditAppender.
    """
    def __init__(self, appender: SQLAlchemyAuditAppender, actor_user_id: Optional[str] = None) -> None:
        self.appender = appender
        self.actor_user_id = actor_user_id

    async def log(self, *, action_type: str, tenant_id: str | None, metadata: dict[str, object] | None = None) -> None:
        """Log audit event to database with actor tracking."""
        from domain.audit.models import AuditEvent
        from uuid import uuid4
        
        event = AuditEvent(
            event_id=str(uuid4()),
            tenant_id=tenant_id,
            category=action_type.split('.')[0] if '.' in action_type else 'system',
            action=action_type,
            actor_user_id=self.actor_user_id,  # Now extracted from request context
            target_type=None,
            target_id=None,
            metadata=metadata or {},
        )
        await self.appender.append(event)


# Database session management

_db_config: DatabaseConfig | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None
_redis_client: redis.Redis | None = None


def get_db_config() -> DatabaseConfig:
    """Get database configuration singleton."""
    global _db_config
    if _db_config is None:
        _db_config = DatabaseConfig.from_env()
    return _db_config


@lru_cache
def get_redis_client() -> redis.Redis:
    """
    Get Redis client singleton for session management.
    
    Reads configuration from environment:
    - REDIS_HOST: Redis server hostname (default: localhost)
    - REDIS_PORT: Redis server port (default: 6379)
    - REDIS_DB: Redis database number (default: 0)
    - REDIS_PASSWORD: Redis password (default: None)
    
    Returns:
        Async Redis client instance
    """
    global _redis_client
    if _redis_client is None:
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db = int(os.getenv("REDIS_DB", "0"))
        password = os.getenv("REDIS_PASSWORD", None)
        
        _redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,  # Return strings instead of bytes
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _redis_client


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get async session maker singleton."""
    global _session_maker
    if _session_maker is None:
        db_config = get_db_config()
        engine = db_config.create_engine()
        _session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    return _session_maker


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide database session for request scope.
    
    Usage in router:
        async def endpoint(session: AsyncSession = Depends(get_db_session)):
            ...
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Repository dependencies (request-scoped via session)

async def get_tenant_repo(session: AsyncSession = Depends(get_db_session)) -> SQLAlchemyTenantRepository:
    """Get tenant repository for current request."""
    return SQLAlchemyTenantRepository(session)


async def get_user_repo(session: AsyncSession = Depends(get_db_session)) -> SQLAlchemyUserRepository:
    """Get user repository for current request."""
    return SQLAlchemyUserRepository(session)


async def get_policy_repo(session: AsyncSession = Depends(get_db_session)) -> SQLAlchemyPolicyRepository:
    """Get policy repository for current request."""
    return SQLAlchemyPolicyRepository(session)


async def get_feature_flag_repo(session: AsyncSession = Depends(get_db_session)) -> SQLAlchemyFeatureFlagRepository:
    """Get feature flag repository for current request."""
    return SQLAlchemyFeatureFlagRepository(session)


async def get_invitation_repo(session: AsyncSession = Depends(get_db_session)) -> SQLAlchemyInvitationRepository:
    """Get invitation repository for current request (database-backed)."""
    return SQLAlchemyInvitationRepository(session)


# Service dependencies

async def get_user_lifecycle(user_repo: SQLAlchemyUserRepository = Depends(get_user_repo)) -> UserLifecycleService:
    """Get user lifecycle service with database-backed repository."""
    return UserLifecycleService(repo=user_repo)  # type: ignore[arg-type]


async def get_invitation_service(
    invitation_repo: SQLAlchemyInvitationRepository = Depends(get_invitation_repo)
) -> InvitationService:
    """Get invitation service (database-backed)."""
    return InvitationService(repo=invitation_repo)  # type: ignore[arg-type]


@lru_cache
def get_auth_registry() -> AuthProviderRegistry:
    return default_registry()


@lru_cache
def get_jwt_service() -> JWTService:
    # Simple static key set for dev / test; rotation to come later.
    ks = JWTKeySet(active_kid="v1", keys={"v1": "dev-secret-key"})
    return JWTService(keys=ks, issuer="modern-backend", audience="modern-backend")


@lru_cache
def get_auth_service() -> AuthenticationService:
    return AuthenticationService(registry=get_auth_registry())


async def get_audit_appender(session: AsyncSession = Depends(get_db_session)) -> SQLAlchemyAuditAppender:
    """Get audit appender for current request (database-backed)."""
    return SQLAlchemyAuditAppender(session)


async def get_current_actor_id(request: Request) -> Optional[str]:
    """
    Extract actor_user_id from request state (set by auth middleware).
    
    Returns None for unauthenticated requests (e.g., login, public endpoints).
    """
    # Check if user was authenticated by get_current_user dependency
    if hasattr(request.state, "user_id"):
        return request.state.user_id
    return None


async def get_audit_service(
    appender: SQLAlchemyAuditAppender = Depends(get_audit_appender),
    actor_user_id: Optional[str] = Depends(get_current_actor_id)
) -> AuditService:
    """Get audit service with actor tracking (database-backed)."""
    return AuditService(appender, actor_user_id=actor_user_id)

