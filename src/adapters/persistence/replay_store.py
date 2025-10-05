"""
IMPL-DB-11: Token replay persistent store implementation.

Provides:
- Database-backed token replay detection (FR-SEC-020)
- PostgreSQL-based JTI (JWT ID) tracking with TTL
- Atomic check-and-set operations for replay prevention
- Automatic cleanup of expired entries

Status: Phase 3 Lane DB-E
Dependencies: IMPL-DB-02 (ORM models), asyncpg
"""
from __future__ import annotations

import time
from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from adapters.persistence.models import Base
from adapters.persistence.db_config import PortableUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, Index
import uuid

# Default tenant_id for non-tenant scenarios (system-wide replay detection)
DEFAULT_TENANT_ID = uuid.UUID('00000000-0000-0000-0000-000000000000')


class TokenReplayRecordModel(Base):
    """
    ORM model for token replay detection records.
    
    Tracks JWT IDs (jti) to prevent token replay attacks (FR-SEC-020).
    """
    __tablename__ = "token_replay_records"
    
    # Primary key is JTI itself for fast lookups
    jti: Mapped[str] = mapped_column(String(255), primary_key=True)
    
    # Expiration timestamp (Unix epoch)
    expires_at: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    
    # First seen timestamp for audit
    registered_at: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Optional tenant context for multi-tenant tracking
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(PortableUUID(), nullable=True, index=True)
    
    __table_args__ = (
        Index("ix_token_replay_expires_at", "expires_at"),
        Index("ix_token_replay_tenant_id", "tenant_id"),
    )


class DatabaseReplayStore:
    """
    Database-backed token replay detection store (FR-SEC-020).
    
    Provides:
    - Atomic check-and-set for replay prevention
    - Persistent storage across server restarts
    - Automatic cleanup of expired entries
    - Multi-tenant support (optional)
    
    Usage:
        store = DatabaseReplayStore(session)
        
        # Register token (returns False if replay detected)
        is_new = await store.register("jti-abc-123", ttl_seconds=3600, tenant_id=tenant_id)
        if not is_new:
            raise ReplayDetectedError("Token already used")
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize database replay store.
        
        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session
    
    async def register(
        self,
        jti: str,
        ttl_seconds: int,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """
        Register a token JTI; returns False if replay detected (FR-SEC-020).
        
        Atomically checks if JTI exists and is not expired. If not present or expired,
        registers the new entry. If present and not expired, returns False (replay).
        
        Args:
            jti: JWT ID (unique token identifier)
            ttl_seconds: Time-to-live in seconds (typically token exp - now)
            tenant_id: Optional tenant ID for multi-tenant tracking
        
        Returns:
            True if token registered successfully (first use)
            False if token already registered and not expired (replay detected)
        """
        now = time.time()
        expires_at = now + ttl_seconds
        
        # Check if JTI already exists and is not expired (globally unique for FR-SEC-020)
        # JTI must be globally unique to prevent superadmin token replay across tenants
        query = select(TokenReplayRecordModel).where(
            TokenReplayRecordModel.jti == jti
        )
        result = await self.session.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Check if expired
            if existing.expires_at > now:
                # Not expired - replay detected
                return False
            else:
                # Expired - delete old entry and register new one
                await self.session.delete(existing)
                await self.session.flush()
        
        # Register new entry
        record = TokenReplayRecordModel(
            jti=jti,
            expires_at=expires_at,
            registered_at=now,
            tenant_id=tenant_id,
        )
        
        try:
            self.session.add(record)
            await self.session.flush()
            return True
        except IntegrityError:
            # Race condition: another request registered same JTI concurrently
            await self.session.rollback()
            return False
    
    async def is_replayed(self, jti: str) -> bool:
        """
        Check if token has been used before (without registering).
        
        Args:
            jti: JWT ID to check
        
        Returns:
            True if token exists and is not expired (replay)
            False if token not found or expired
        """
        now = time.time()
        
        result = await self.session.execute(
            select(TokenReplayRecordModel).where(TokenReplayRecordModel.jti == jti)
        )
        existing = result.scalar_one_or_none()
        
        if existing and existing.expires_at > now:
            return True
        return False
    
    async def cleanup_expired(self, batch_size: int = 1000) -> int:
        """
        Remove expired replay records (maintenance operation).
        
        Should be called periodically (e.g., daily cron job) to prevent
        table bloat.
        
        Args:
            batch_size: Maximum number of records to delete per batch
        
        Returns:
            Number of records deleted
        """
        now = time.time()
        
        result = await self.session.execute(
            delete(TokenReplayRecordModel)
            .where(TokenReplayRecordModel.expires_at <= now)
            .execution_options(synchronize_session=False)
        )
        
        deleted_count = result.rowcount or 0
        await self.session.commit()
        
        return deleted_count
    
    async def count_active(self, tenant_id: Optional[uuid.UUID] = None) -> int:
        """
        Count active (non-expired) replay records.
        
        Useful for monitoring and capacity planning.
        
        Args:
            tenant_id: Optional tenant filter
        
        Returns:
            Number of active replay records
        """
        from sqlalchemy import func
        
        now = time.time()
        
        query = select(func.count()).select_from(TokenReplayRecordModel).where(
            TokenReplayRecordModel.expires_at > now
        )
        
        if tenant_id:
            query = query.where(TokenReplayRecordModel.tenant_id == tenant_id)
        
        result = await self.session.execute(query)
        count = result.scalar_one()
        
        return count


# TODO (Phase 4): Add Alembic migration for token_replay_records table
# TODO (Phase 4): Add scheduled cleanup job (daily cron)
# TODO (Phase 4): Add metrics for replay detection rate
