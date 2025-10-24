"""V1.0.0 Consolidated Schema - Single Baseline Migration

Revision ID: v1_0_0_consolidated
Revises: 
Create Date: 2025-10-21 00:00:00.000000+00:00

This migration consolidates all schema changes from development into a single
V1.0.0 baseline for production deployment. It replaces 13 fragmented migrations
with a clean, idempotent schema definition.

CONSOLIDATED MIGRATIONS:
- 20251017_1020_v1_0_0_base_schema.py (initial tables)
- 20251017_0645_5b0206f95039_add_user_details_table.py
- 20251017_1807_824535e758b7_add_status_to_policies_and_feature_flags.py
- 20251018_1306_3df50b046835_rename_tenant_soft_deleted_to_disabled.py
- 20251020_0628_56b3e20010a2_drop_global_email_unique_constraint.py
- 20251020_0628_9a6e88ad1601_ensure_per_tenant_email_unique_index.py
- 20251020_0629_3da4ba72b3b5_add_schema_version_metadata_table.py
- 20251020_1747_0c34fb45b7a8_create_roles_table.py
- 20251020_1747_6972634478c6_create_user_roles_table.py
- 20251020_1748_31a51a6816b1_seed_system_roles.py

FIXES APPLIED:
1. roles.id (not role_id) - matches test expectations
2. user_details audit fields nullable - matches models.py
3. user_details constraint naming standardized (*_pkey, *_fkey)
4. user_roles: UUID role_id + audit fields (assigned_at, assigned_by)
5. Removed old user_roles VARCHAR(50) role_id
6. All CASCADE policies explicit
7. tenant status includes 'disabled' (not just soft_deleted)

TABLES CREATED (15):
- tenants (tenant isolation root)
- users (tenant-scoped principals)
- roles (system + custom tenant roles) 
- user_roles (user-role assignments)
- user_details (profile extensions)
- user_mfa (MFA enrollment)
- invitations (pending invites)
- password_reset_requests (reset tokens)
- policies (authorization rules)
- policy_evaluation_logs (policy audit trail)
- audit_events (compliance log - NO FKs)
- feature_flags (toggles)
- key_rotation_records (signing key lifecycle)
- token_replay_records (JWT replay detection)
- schema_version (migration metadata)

SYSTEM ROLES SEEDED (3):
- superadmin: 00000000-0000-0000-0000-000000000001
- tenant_admin: 00000000-0000-0000-0000-000000000002
- user: 00000000-0000-0000-0000-000000000003
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Import PortableUUID for database-agnostic UUID support
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from adapters.persistence.db_config import PortableUUID


# Revision identifiers, used by Alembic
revision: str = 'v1_0_0_consolidated'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# System role UUIDs (fixed for test consistency)
SUPERADMIN_ROLE_ID = '00000000-0000-0000-0000-000000000001'
TENANT_ADMIN_ROLE_ID = '00000000-0000-0000-0000-000000000002'
USER_ROLE_ID = '00000000-0000-0000-0000-000000000003'


def upgrade() -> None:
    """Create all V1.0 tables, indexes, constraints, and seed data."""
    
    # ========================================================================
    # ENUM TYPES
    # ========================================================================
    
    # NOTE: Enum types are automatically created by SQLAlchemy when you use sa.Enum()
    # in column definitions. No need for manual CREATE TYPE statements.
    
    # ========================================================================
    # CORE TABLES
    # ========================================================================
    
    # Tenants table (multi-tenant root)
    op.create_table(
        'tenants',
        sa.Column('tenant_id', PortableUUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('active', 'soft_deleted', 'disabled', name='tenant_status'), 
                  nullable=False, server_default='active'),
        sa.Column('config_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', PortableUUID(), nullable=True),
        sa.Column('updated_by', PortableUUID(), nullable=True),
        sa.PrimaryKeyConstraint('tenant_id', name='tenants_pkey'),
        sa.UniqueConstraint('name', name='tenants_name_key')
    )
    op.create_index('ix_tenants_name', 'tenants', ['name'])
    op.create_index('ix_tenants_status_created_at', 'tenants', ['status', 'created_at'])
    
    # Users table (tenant-scoped principals)
    op.create_table(
        'users',
        sa.Column('user_id', PortableUUID(), nullable=False),
        sa.Column('tenant_id', PortableUUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('invited', 'active', 'disabled', name='user_status'), 
                  nullable=False, server_default='invited'),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', PortableUUID(), nullable=True),
        sa.Column('updated_by', PortableUUID(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], 
                               name='users_tenant_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', name='users_pkey')
    )
    # Per-tenant email uniqueness (V1.0 requirement)
    op.create_index('ix_users_email_tenant', 'users', ['email', 'tenant_id'], unique=True)
    op.create_index('ix_users_tenant_status', 'users', ['tenant_id', 'status'])
    
    # Roles table (system + custom tenant roles)
    op.create_table(
        'roles',
        sa.Column('id', PortableUUID(), nullable=False),  # NOTE: 'id' not 'role_id' per PK_NAMING_ANALYSIS.md
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('tenant_id', PortableUUID(), nullable=True),  # NULL for system roles
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, 
                  server_default=sa.text("'[]'::jsonb")),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', PortableUUID(), nullable=True),
        sa.Column('updated_by', PortableUUID(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], 
                               name='roles_tenant_id_fkey', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], 
                               name='roles_created_by_fkey', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.user_id'], 
                               name='roles_updated_by_fkey', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='roles_pkey'),
        sa.UniqueConstraint('name', 'tenant_id', name='unique_role_name_per_tenant')
    )
    op.create_index('idx_roles_tenant', 'roles', ['tenant_id'])
    op.create_index('idx_roles_system', 'roles', ['is_system'], 
                   postgresql_where=sa.text('is_system = true'))
    
    # User-Roles junction table (WITH AUDIT FIELDS - fixed from old schema)
    op.create_table(
        'user_roles',
        sa.Column('user_id', PortableUUID(), nullable=False),
        sa.Column('role_id', PortableUUID(), nullable=False),  # UUID not VARCHAR(50)
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('assigned_by', PortableUUID(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], 
                               name='user_roles_user_id_fkey', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'],  # References roles.id not roles.role_id
                               name='user_roles_role_id_fkey', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.user_id'], 
                               name='user_roles_assigned_by_fkey', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('user_id', 'role_id', name='user_roles_pkey')
    )
    op.create_index('idx_user_roles_user', 'user_roles', ['user_id'])
    op.create_index('idx_user_roles_role', 'user_roles', ['role_id'])
    
    # User details table (profile extensions - FIXED CONSTRAINTS)
    op.create_table(
        'user_details',
        sa.Column('user_id', PortableUUID(), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('photo_display_url', sa.String(length=512), nullable=True),
        sa.Column('photo_thumbnail_url', sa.String(length=512), nullable=True),
        sa.Column('photo_avatar_url', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', PortableUUID(), nullable=True),  # NULLABLE (matches models.py)
        sa.Column('updated_by', PortableUUID(), nullable=True),  # NULLABLE (matches models.py)
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], 
                               name='user_details_user_id_fkey', ondelete='CASCADE'),  # STANDARD NAMING
        sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], 
                               name='user_details_created_by_fkey', ondelete='SET NULL'),  # STANDARD NAMING
        sa.ForeignKeyConstraint(['updated_by'], ['users.user_id'], 
                               name='user_details_updated_by_fkey', ondelete='SET NULL'),  # STANDARD NAMING
        sa.PrimaryKeyConstraint('user_id', name='user_details_pkey')  # STANDARD NAMING
    )
    op.create_index('ix_user_details_created_at', 'user_details', ['created_at'])
    op.create_index('ix_user_details_updated_at', 'user_details', ['updated_at'])
    
    # User MFA table
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
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], 
                               name='user_mfa_user_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'factor_type', name='user_mfa_pkey')
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
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], 
                               name='invitations_tenant_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('invitation_id', name='invitations_pkey')
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
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], 
                               name='password_reset_requests_user_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('reset_id', name='password_reset_requests_pkey'),
        sa.UniqueConstraint('token_hash', name='password_reset_requests_token_hash_key')
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
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', PortableUUID(), nullable=True),
        sa.Column('updated_by', PortableUUID(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], 
                               name='policies_tenant_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('policy_id', name='policies_pkey')
    )
    op.create_index('ix_policies_tenant_id', 'policies', ['tenant_id'])
    op.create_index('ix_policies_created_at', 'policies', ['created_at'])
    op.create_index('ix_policies_status', 'policies', ['status'])
    
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
        sa.ForeignKeyConstraint(['policy_id'], ['policies.policy_id'], 
                               name='policy_evaluation_logs_policy_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('eval_id', name='policy_evaluation_logs_pkey')
    )
    op.create_index('ix_policy_eval_logs_policy_created', 'policy_evaluation_logs', ['policy_id', 'created_at'])
    op.create_index('ix_policy_eval_logs_tenant_created', 'policy_evaluation_logs', ['tenant_id', 'created_at'])
    op.create_index('ix_policy_eval_logs_decision_created', 'policy_evaluation_logs', ['decision', 'created_at'])
    
    # Audit events table (NO FOREIGN KEY CONSTRAINTS - audit integrity principle)
    op.create_table(
        'audit_events',
        sa.Column('event_id', PortableUUID(), nullable=False),
        sa.Column('tenant_id', PortableUUID(), nullable=True),
        sa.Column('actor_user_id', PortableUUID(), nullable=True),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('target_ref', sa.String(length=255), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        # NOTE: NO ForeignKeyConstraints - audit integrity (never blocks operations)
        sa.PrimaryKeyConstraint('event_id', name='audit_events_pkey')
    )
    op.create_index('ix_audit_events_tenant_created', 'audit_events', ['tenant_id', 'created_at'])
    op.create_index('ix_audit_events_action_created', 'audit_events', ['action_type', 'created_at'])
    
    # Feature flags table
    op.create_table(
        'feature_flags',
        sa.Column('flag_id', PortableUUID(), nullable=False),
        sa.Column('tenant_id', PortableUUID(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('state', sa.Enum('enabled', 'disabled', name='flag_state'), 
                  nullable=False, server_default='disabled'),
        sa.Column('variant', sa.String(length=50), nullable=True),
        sa.Column('rules', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', PortableUUID(), nullable=True),
        sa.Column('updated_by', PortableUUID(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], 
                               name='feature_flags_tenant_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('flag_id', name='feature_flags_pkey')
    )
    op.create_index('ix_feature_flags_tenant_key', 'feature_flags', ['tenant_id', 'key'], unique=True)
    op.create_index('ix_feature_flags_state', 'feature_flags', ['state'])
    op.create_index('ix_feature_flags_status', 'feature_flags', ['status'])
    
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
        sa.PrimaryKeyConstraint('key_version', name='key_rotation_records_pkey')
    )
    
    # Token replay records table (JWT replay detection)
    op.create_table(
        'token_replay_records',
        sa.Column('jti', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.Float(), nullable=False),
        sa.Column('registered_at', sa.Float(), nullable=False),
        sa.Column('tenant_id', PortableUUID(), nullable=True),
        sa.PrimaryKeyConstraint('jti', name='token_replay_records_pkey')
    )
    op.create_index('ix_token_replay_expires_at', 'token_replay_records', ['expires_at'])
    op.create_index('ix_token_replay_tenant_id', 'token_replay_records', ['tenant_id'])
    
    # Schema version metadata table (V1.0 tracking)
    op.create_table(
        'schema_version',
        sa.Column('version', sa.String(20), nullable=False),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=False, 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('checksum', sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint('version', name='schema_version_pkey')
    )
    
    # ========================================================================
    # SEED DATA
    # ========================================================================
    
    # Insert V1.0 schema version marker
    op.execute("""
        INSERT INTO schema_version (version, description)
        VALUES (
            '1.0.0', 
            'V1.0 consolidated schema: All tables, per-tenant email uniqueness, role management, audit metadata'
        )
        ON CONFLICT (version) DO NOTHING
    """)
    
    # Insert 3 system roles with fixed UUIDs
    op.execute(f"""
        INSERT INTO roles (id, name, tenant_id, is_system, permissions, description, created_at, updated_at)
        VALUES 
        ('{SUPERADMIN_ROLE_ID}'::uuid, 'superadmin', NULL, TRUE, 
         '["*"]'::jsonb,
         'System administrator with cross-tenant access and all permissions',
         NOW(), NOW()),
        ('{TENANT_ADMIN_ROLE_ID}'::uuid, 'tenant_admin', NULL, TRUE,
         '["tenant:*", "users:*", "roles:create", "roles:update", "roles:delete", "policies:*"]'::jsonb,
         'Tenant administrator with full control within tenant scope',
         NOW(), NOW()),
        ('{USER_ROLE_ID}'::uuid, 'user', NULL, TRUE,
         '["users:read_own", "profile:update_own"]'::jsonb,
         'Standard authenticated user with read-only access to own resources',
         NOW(), NOW())
        ON CONFLICT (name, tenant_id) DO NOTHING
    """)


def downgrade() -> None:
    """Drop all V1.0 tables and enum types.
    
    WARNING: This is destructive and will delete all data.
    V1.0 is forward-only; downgrade not supported in production.
    """
    # Drop tables in reverse dependency order
    op.drop_table('schema_version')
    op.drop_table('token_replay_records')
    op.drop_table('key_rotation_records')
    op.drop_table('feature_flags')
    op.drop_table('audit_events')
    op.drop_table('policy_evaluation_logs')
    op.drop_table('policies')
    op.drop_table('password_reset_requests')
    op.drop_table('invitations')
    op.drop_table('user_mfa')
    op.drop_table('user_details')
    op.drop_table('user_roles')
    op.drop_table('roles')
    op.drop_table('users')
    op.drop_table('tenants')
    
    # Drop enum types (PostgreSQL-specific, safe to run on SQLite)
    op.execute("DROP TYPE IF EXISTS mfa_factor_type")
    op.execute("DROP TYPE IF EXISTS flag_state")
    op.execute("DROP TYPE IF EXISTS decision")
    op.execute("DROP TYPE IF EXISTS user_status")
    op.execute("DROP TYPE IF EXISTS tenant_status")
