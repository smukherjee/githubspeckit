"""v1.0.0 Base Schema - Consolidated Initial Migration

Revision ID: v1_0_0_base
Revises: 
Create Date: 2025-10-17 10:20:00.000000+00:00

This migration consolidates all schema changes from the initial development phase
into a single base migration for the v1.0 release.

Consolidated from:
- 9f85fdd0f4d0: Initial schema baseline (all core tables)
- 8c01924a527d: Token replay records table (JWT replay protection)
- 94da136ac201: Remove audit_events FK constraints (audit integrity)

Tables Created:
- tenants: Multi-tenant root entity
- users: Tenant-scoped user accounts
- user_roles: User-to-role associations
- invitations: Pending user invitations
- password_reset_requests: Password reset tokens
- policies: Authorization policies
- policy_evaluation_logs: Policy evaluation audit trail
- audit_events: Compliance audit log (NO FK constraints)
- feature_flags: Feature toggles
- key_rotation_records: Signing key lifecycle
- user_mfa: MFA enrollment (deferred)
- token_replay_records: JWT replay detection
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Import PortableUUID for database-agnostic UUID support
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from adapters.persistence.db_config import PortableUUID


# revision identifiers, used by Alembic.
revision: str = 'v1_0_0_base'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables and indexes for v1.0 release schema."""
    
    # ========================================================================
    # CORE TABLES (from 9f85fdd0f4d0)
    # ========================================================================
    
    # Tenants table (multi-tenant root)
    op.create_table(
        'tenants',
        sa.Column('tenant_id', PortableUUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('active', 'soft_deleted', name='tenant_status'), nullable=False, server_default='active'),
        sa.Column('config_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', PortableUUID(), nullable=True),
        sa.Column('updated_by', PortableUUID(), nullable=True),
        sa.PrimaryKeyConstraint('tenant_id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_tenants_name', 'tenants', ['name'])
    op.create_index('ix_tenants_status_created_at', 'tenants', ['status', 'created_at'])
    
    # Users table (tenant-scoped principals)
    op.create_table(
        'users',
        sa.Column('user_id', PortableUUID(), nullable=False),
        sa.Column('tenant_id', PortableUUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('invited', 'active', 'disabled', name='user_status'), nullable=False, server_default='invited'),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', PortableUUID(), nullable=True),
        sa.Column('updated_by', PortableUUID(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index('ix_users_tenant_email', 'users', ['tenant_id', 'email'], unique=True)
    op.create_index('ix_users_tenant_status', 'users', ['tenant_id', 'status'])
    
    # User roles association table
    op.create_table(
        'user_roles',
        sa.Column('user_id', PortableUUID(), nullable=False),
        sa.Column('role_id', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id')
    )
    
    # Invitations table
    op.create_table(
        'invitations',
        sa.Column('invitation_id', PortableUUID(), nullable=False),
        sa.Column('tenant_id', PortableUUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('invitation_id')
    )
    op.create_index('ix_invitations_tenant_email', 'invitations', ['tenant_id', 'email'])
    op.create_index('ix_invitations_expires_at', 'invitations', ['expires_at'])
    
    # Password reset requests table
    op.create_table(
        'password_reset_requests',
        sa.Column('reset_id', PortableUUID(), nullable=False),
        sa.Column('user_id', PortableUUID(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('reset_id'),
        sa.UniqueConstraint('token_hash')
    )
    op.create_index('ix_password_resets_user_expires', 'password_reset_requests', ['user_id', 'expires_at'])
    op.create_index('ix_password_resets_token_hash', 'password_reset_requests', ['token_hash'])
    
    # Policies table
    op.create_table(
        'policies',
        sa.Column('policy_id', PortableUUID(), nullable=False),
        sa.Column('tenant_id', PortableUUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('rules', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', PortableUUID(), nullable=True),
        sa.Column('updated_by', PortableUUID(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('policy_id')
    )
    op.create_index('ix_policies_tenant_id', 'policies', ['tenant_id'])
    op.create_index('ix_policies_created_at', 'policies', ['created_at'])
    
    # Policy evaluation logs table
    op.create_table(
        'policy_evaluation_logs',
        sa.Column('eval_id', PortableUUID(), nullable=False),
        sa.Column('policy_id', PortableUUID(), nullable=False),
        sa.Column('decision', sa.Enum('ALLOW', 'DENY', 'ABSTAIN', name='decision'), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('tenant_id', PortableUUID(), nullable=False),
        sa.Column('user_id', PortableUUID(), nullable=False),
        sa.Column('correlation_id', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.policy_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('eval_id')
    )
    op.create_index('ix_policy_eval_logs_policy_created', 'policy_evaluation_logs', ['policy_id', 'created_at'])
    op.create_index('ix_policy_eval_logs_tenant_created', 'policy_evaluation_logs', ['tenant_id', 'created_at'])
    op.create_index('ix_policy_eval_logs_decision_created', 'policy_evaluation_logs', ['decision', 'created_at'])
    
    # ========================================================================
    # AUDIT EVENTS TABLE (from 94da136ac201 - NO FK CONSTRAINTS)
    # ========================================================================
    
    # Audit events table - NO FOREIGN KEY CONSTRAINTS (audit integrity principle)
    # Rationale: Audit tables must never block operations due to FK violations
    # Application layer handles referential integrity
    op.create_table(
        'audit_events',
        sa.Column('event_id', PortableUUID(), nullable=False),
        sa.Column('tenant_id', PortableUUID(), nullable=True),
        sa.Column('actor_user_id', PortableUUID(), nullable=True),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('target_ref', sa.String(length=255), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        # NOTE: NO ForeignKeyConstraints - audit integrity
        sa.PrimaryKeyConstraint('event_id')
    )
    op.create_index('ix_audit_events_tenant_created', 'audit_events', ['tenant_id', 'created_at'])
    op.create_index('ix_audit_events_action_created', 'audit_events', ['action_type', 'created_at'])
    
    # ========================================================================
    # FEATURE FLAGS AND OPERATIONAL TABLES
    # ========================================================================
    
    # Feature flags table
    op.create_table(
        'feature_flags',
        sa.Column('flag_id', PortableUUID(), nullable=False),
        sa.Column('tenant_id', PortableUUID(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('state', sa.Enum('enabled', 'disabled', name='flag_state'), nullable=False, server_default='disabled'),
        sa.Column('variant', sa.String(length=50), nullable=True),
        sa.Column('rules', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', PortableUUID(), nullable=True),
        sa.Column('updated_by', PortableUUID(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('flag_id')
    )
    op.create_index('ix_feature_flags_tenant_key', 'feature_flags', ['tenant_id', 'key'], unique=True)
    op.create_index('ix_feature_flags_state', 'feature_flags', ['state'])
    
    # Key rotation records table
    op.create_table(
        'key_rotation_records',
        sa.Column('key_version', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('retired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('algorithm', sa.String(length=50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', PortableUUID(), nullable=True),
        sa.PrimaryKeyConstraint('key_version')
    )
    
    # User MFA table (deferred implementation)
    op.create_table(
        'user_mfa',
        sa.Column('user_id', PortableUUID(), nullable=False),
        sa.Column('factor_type', sa.Enum('totp', 'webauthn', name='mfa_factor_type'), nullable=False),
        sa.Column('enrolled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('secret_hash', sa.String(length=255), nullable=True),
        sa.Column('credential_public_key', sa.LargeBinary(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', PortableUUID(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'factor_type')
    )
    
    # ========================================================================
    # TOKEN REPLAY RECORDS TABLE (from 8c01924a527d)
    # ========================================================================
    
    # Token replay records for JWT replay detection (FR-SEC-020, IMPL-DB-11)
    # JTI is globally unique (single PK) to prevent superadmin token replay across tenants
    # tenant_id is optional for multi-tenant tracking
    op.create_table(
        'token_replay_records',
        sa.Column('jti', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.Float(), nullable=False),
        sa.Column('registered_at', sa.Float(), nullable=False),
        sa.Column('tenant_id', PortableUUID(), nullable=True),
        sa.PrimaryKeyConstraint('jti')
    )
    op.create_index('ix_token_replay_expires_at', 'token_replay_records', ['expires_at'])
    op.create_index('ix_token_replay_tenant_id', 'token_replay_records', ['tenant_id'])


def downgrade() -> None:
    """Drop all tables and enum types."""
    # Drop tables in reverse dependency order
    op.drop_table('token_replay_records')
    op.drop_table('user_mfa')
    op.drop_table('key_rotation_records')
    op.drop_table('feature_flags')
    op.drop_table('audit_events')
    op.drop_table('policy_evaluation_logs')
    op.drop_table('policies')
    op.drop_table('password_reset_requests')
    op.drop_table('invitations')
    op.drop_table('user_roles')
    op.drop_table('users')
    op.drop_table('tenants')
    
    # Drop enum types (PostgreSQL-specific, safe to run on SQLite)
    # SQLite ignores these statements
    op.execute("DROP TYPE IF EXISTS mfa_factor_type")
    op.execute("DROP TYPE IF EXISTS decision")
    op.execute("DROP TYPE IF EXISTS flag_state")
    op.execute("DROP TYPE IF EXISTS user_status")
    op.execute("DROP TYPE IF EXISTS tenant_status")
