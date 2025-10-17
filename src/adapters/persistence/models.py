"""
IMPL-DB-02: SQLAlchemy ORM models for all entities.

Implements async-compatible SQLAlchemy 2.x declarative models matching
the data model specification (specs/001-modern-enterprise-grade/data-model.md).

Architecture:
- Uses declarative_base for consistency with async patterns
- All timestamps in UTC via default factories
- Indexes defined per data-model.md specification
- Foreign keys with explicit ON DELETE behavior (FR-002, FR-018)
- Soft delete via status enums (no physical deletion for tenants/users)

Entities:
- Tenant (multi-tenant root)
- User (with roles association via user_roles)
- Invitation (pending user onboarding)
- PasswordResetRequest (password reset flow)
- Policy (authorization rules)
- PolicyEvaluationLog (evaluation audit trail)
- AuditEvent (compliance log)
- FeatureFlag (toggles)
- KeyRotationRecord (signing key lifecycle)
- UserMFA (MFA enrollment, deferred)

Status: Phase 3 Lane DB-A
Dependencies: TEST-DB-01 (defines behavioral contract)
Next: IMPL-DB-03 (Alembic migrations)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    String, Integer, DateTime, Boolean, JSON, ForeignKey,
    Index, Enum as SQLEnum, Text
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

import enum

# Import portable UUID type for database-agnostic UUID support
from .db_config import PortableUUID


# Declarative base for all models
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


# Enum types (mirrored from domain models)

class TenantStatusEnum(str, enum.Enum):
    """Tenant lifecycle status (FR-018: soft delete)."""
    active = "active"
    soft_deleted = "soft_deleted"


class UserStatusEnum(str, enum.Enum):
    """User account status (FR-018: soft delete via disabled)."""
    invited = "invited"
    active = "active"
    disabled = "disabled"


class FlagStateEnum(str, enum.Enum):
    """Feature flag state."""
    enabled = "enabled"
    disabled = "disabled"


class DecisionEnum(str, enum.Enum):
    """Policy evaluation decision (FR-030)."""
    ALLOW = "ALLOW"
    DENY = "DENY"
    ABSTAIN = "ABSTAIN"


class MFAFactorTypeEnum(str, enum.Enum):
    """MFA factor types (deferred implementation)."""
    totp = "totp"
    webauthn = "webauthn"


# ORM Models

class TenantModel(Base):
    """
    Tenant entity (FR-002: multi-tenant isolation root).
    
    Soft delete via status=soft_deleted (FR-018).
    All tenant-scoped entities FK to tenant_id.
    """
    __tablename__ = "tenants"

    tenant_id: Mapped[UUID] = mapped_column(PortableUUID(), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[TenantStatusEnum] = mapped_column(
        SQLEnum(TenantStatusEnum, name="tenant_status"),
        default=TenantStatusEnum.active,
        nullable=False
    )
    config_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Audit metadata (FR-077)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(PortableUUID(), nullable=True)
    updated_by: Mapped[Optional[UUID]] = mapped_column(PortableUUID(), nullable=True)

    # Indexes per data-model.md
    __table_args__ = (
        Index("ix_tenants_name", "name"),
        Index("ix_tenants_status_created_at", "status", "created_at"),
    )


class UserModel(Base):
    """
    User entity (FR-002: tenant-scoped principal).
    
    Soft delete via status=disabled (FR-018).
    Roles stored in separate association table (user_roles).
    """
    __tablename__ = "users"

    user_id: Mapped[UUID] = mapped_column(PortableUUID(), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PortableUUID(),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),  # Delete users if tenant deleted
        nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[UserStatusEnum] = mapped_column(
        SQLEnum(UserStatusEnum, name="user_status"),
        default=UserStatusEnum.invited,
        nullable=False
    )
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Audit metadata (FR-077)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(PortableUUID(), nullable=True)
    updated_by: Mapped[Optional[UUID]] = mapped_column(PortableUUID(), nullable=True)

    # Indexes per data-model.md
    __table_args__ = (
        Index("ix_users_tenant_email", "tenant_id", "email", unique=True),
        Index("ix_users_tenant_status", "tenant_id", "status"),
    )


class UserRoleModel(Base):
    """
    User-Role association table (many-to-many).
    
    Role IDs are string enums (superadmin, tenant_admin, analyst, standard, etc.).
    """
    __tablename__ = "user_roles"

    user_id: Mapped[UUID] = mapped_column(
        PortableUUID(),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True
    )
    role_id: Mapped[str] = mapped_column(String(50), primary_key=True)


class InvitationModel(Base):
    """
    Invitation entity (pending user onboarding).
    
    Token stored as SHA-256 hash for security.
    Expires after configured TTL (FR-020).
    """
    __tablename__ = "invitations"

    invitation_id: Mapped[UUID] = mapped_column(PortableUUID(), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PortableUUID(),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 hex
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Indexes per data-model.md
    __table_args__ = (
        Index("ix_invitations_tenant_email", "tenant_id", "email"),
        Index("ix_invitations_expires_at", "expires_at"),
    )


class PasswordResetRequestModel(Base):
    """
    Password reset request entity (single-use token flow).
    
    Token stored as SHA-256 hash.
    Expires after configured TTL (FR-049).
    """
    __tablename__ = "password_reset_requests"

    reset_id: Mapped[UUID] = mapped_column(PortableUUID(), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        PortableUUID(),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # SHA-256 hex
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Indexes per data-model.md
    __table_args__ = (
        Index("ix_password_resets_user_expires", "user_id", "expires_at"),
        Index("ix_password_resets_token_hash", "token_hash"),  # Fast lookup
    )


class PolicyModel(Base):
    """
    Policy entity (authorization rules, FR-030).
    
    Rules stored as JSON array (PolicyRule structures).
    Supports versioning via version field.
    """
    __tablename__ = "policies"

    policy_id: Mapped[UUID] = mapped_column(PortableUUID(), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PortableUUID(),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rules: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # Array of PolicyRule dicts
    
    # Audit metadata (FR-077)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(PortableUUID(), nullable=True)
    updated_by: Mapped[Optional[UUID]] = mapped_column(PortableUUID(), nullable=True)

    # Indexes per data-model.md
    __table_args__ = (
        Index("ix_policies_tenant_id", "tenant_id"),
        Index("ix_policies_created_at", "created_at"),
    )


class PolicyEvaluationLogModel(Base):
    """
    Policy evaluation audit log (FR-030, FR-034).
    
    Records each policy evaluation with latency metrics.
    Append-only (no updates).
    """
    __tablename__ = "policy_evaluation_logs"

    eval_id: Mapped[UUID] = mapped_column(PortableUUID(), primary_key=True)
    policy_id: Mapped[UUID] = mapped_column(
        PortableUUID(),
        ForeignKey("policies.policy_id", ondelete="CASCADE"),
        nullable=False
    )
    decision: Mapped[DecisionEnum] = mapped_column(
        SQLEnum(DecisionEnum, name="decision"),
        nullable=False
    )
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    tenant_id: Mapped[UUID] = mapped_column(PortableUUID(), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PortableUUID(), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Indexes per data-model.md
    __table_args__ = (
        Index("ix_policy_eval_logs_policy_created", "policy_id", "created_at"),
        Index("ix_policy_eval_logs_tenant_created", "tenant_id", "created_at"),
        Index("ix_policy_eval_logs_decision_created", "decision", "created_at"),
    )


class AuditEventModel(Base):
    """
    System-wide audit event log (FR-005, FR-077).
    
    Tenant nullable for system/global events.
    Metadata JSONB with redaction enforced at adapter layer (C-007).
    Append-only (no updates).
    """
    __tablename__ = "audit_events"

    event_id: Mapped[UUID] = mapped_column(PortableUUID(), primary_key=True)
    tenant_id: Mapped[Optional[UUID]] = mapped_column(
        PortableUUID(),
        nullable=True
    )
    actor_user_id: Mapped[Optional[UUID]] = mapped_column(
        PortableUUID(),
        nullable=True
    )
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    event_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)  # Column name 'metadata', attribute name 'event_metadata'
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Indexes per data-model.md
    __table_args__ = (
        Index("ix_audit_events_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_events_action_created", "action_type", "created_at"),
    )


class FeatureFlagModel(Base):
    """
    Feature flag entity (toggles for gradual rollout).
    
    Tenant nullable for global flags.
    Rules stored as JSONB for future targeting logic.
    """
    __tablename__ = "feature_flags"

    flag_id: Mapped[UUID] = mapped_column(PortableUUID(), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PortableUUID(),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[FlagStateEnum] = mapped_column(
        SQLEnum(FlagStateEnum, name="flag_state"),
        default=FlagStateEnum.disabled,
        nullable=False
    )
    variant: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    rules: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Audit metadata (FR-077)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(PortableUUID(), nullable=True)
    updated_by: Mapped[Optional[UUID]] = mapped_column(PortableUUID(), nullable=True)

    # Indexes per data-model.md
    __table_args__ = (
        Index("ix_feature_flags_tenant_key", "tenant_id", "key", unique=True),
        Index("ix_feature_flags_state", "state"),
    )


class KeyRotationRecordModel(Base):
    """
    Key rotation lifecycle record (FR-006: transparent key rotation).
    
    Tracks signing key versions with activation/retirement timestamps.
    """
    __tablename__ = "key_rotation_records"

    key_version: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retired_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(PortableUUID(), nullable=True)


class UserMFAModel(Base):
    """
    MFA enrollment record (deferred implementation per FR-061-065).
    
    One row per user per factor type.
    Secret/credential stored hashed or encrypted.
    """
    __tablename__ = "user_mfa"

    user_id: Mapped[UUID] = mapped_column(
        PortableUUID(),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True
    )
    factor_type: Mapped[MFAFactorTypeEnum] = mapped_column(
        SQLEnum(MFAFactorTypeEnum, name="mfa_factor_type"),
        primary_key=True
    )
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    secret_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # TOTP secret hash
    credential_public_key: Mapped[Optional[bytes]] = mapped_column(nullable=True)  # WebAuthn public key
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(PortableUUID(), nullable=True)


class UserDetailsModel(Base):
    """
    User profile details entity (FR-003-user-profile-details).
    
    Extended profile information with optional photo URLs.
    One-to-one with users table via user_id primary key.
    """
    __tablename__ = "user_details"

    user_id: Mapped[UUID] = mapped_column(
        PortableUUID(),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photo_display_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    photo_thumbnail_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    photo_avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    # Audit metadata (FR-077)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PortableUUID(),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True
    )
    updated_by: Mapped[Optional[UUID]] = mapped_column(
        PortableUUID(),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True
    )

    # Indexes
    __table_args__ = (
        Index("ix_user_details_created_at", "created_at"),
        Index("ix_user_details_updated_at", "updated_at"),
    )
