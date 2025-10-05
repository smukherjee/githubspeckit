"""initial_schema_baseline

Revision ID: 9f85fdd0f4d0
Revises: 
Create Date: 2025-10-05 03:56:34.676030+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f85fdd0f4d0'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all initial tables and indexes for baseline schema."""
    # Note: Enum types are created automatically by SQLAlchemy when creating tables
    
    # Tenants table (multi-tenant root)
    op.create_table(
        'tenants',
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('active', 'soft_deleted', name='tenant_status'), nullable=False, server_default='active'),
        sa.Column('config_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint('tenant_id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_tenants_name', 'tenants', ['name'])
    op.create_index('ix_tenants_status_created_at', 'tenants', ['status', 'created_at'])
    
    # Users table (tenant-scoped principals)
    op.create_table(
        'users',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('invited', 'active', 'disabled', name='user_status'), nullable=False, server_default='invited'),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index('ix_users_tenant_email', 'users', ['tenant_id', 'email'], unique=True)
    op.create_index('ix_users_tenant_status', 'users', ['tenant_id', 'status'])
    
    # User roles association table
    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role_id', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id')
    )
    
    # Invitations table
    op.create_table(
        'invitations',
        sa.Column('invitation_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
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
        sa.Column('reset_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
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
        sa.Column('policy_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('rules', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('policy_id')
    )
    op.create_index('ix_policies_tenant_id', 'policies', ['tenant_id'])
    op.create_index('ix_policies_created_at', 'policies', ['created_at'])
    
    # Policy evaluation logs table
    op.create_table(
        'policy_evaluation_logs',
        sa.Column('eval_id', sa.UUID(), nullable=False),
        sa.Column('policy_id', sa.UUID(), nullable=False),
        sa.Column('decision', sa.Enum('ALLOW', 'DENY', 'ABSTAIN', name='decision'), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('correlation_id', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.policy_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('eval_id')
    )
    op.create_index('ix_policy_eval_logs_policy_created', 'policy_evaluation_logs', ['policy_id', 'created_at'])
    op.create_index('ix_policy_eval_logs_tenant_created', 'policy_evaluation_logs', ['tenant_id', 'created_at'])
    op.create_index('ix_policy_eval_logs_decision_created', 'policy_evaluation_logs', ['decision', 'created_at'])
    
    # Audit events table
    op.create_table(
        'audit_events',
        sa.Column('event_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=True),
        sa.Column('actor_user_id', sa.UUID(), nullable=True),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('target_ref', sa.String(length=255), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('event_id')
    )
    op.create_index('ix_audit_events_tenant_created', 'audit_events', ['tenant_id', 'created_at'])
    op.create_index('ix_audit_events_action_created', 'audit_events', ['action_type', 'created_at'])
    
    # Feature flags table
    op.create_table(
        'feature_flags',
        sa.Column('flag_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('state', sa.Enum('enabled', 'disabled', name='flag_state'), nullable=False, server_default='disabled'),
        sa.Column('variant', sa.String(length=50), nullable=True),
        sa.Column('rules', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
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
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint('key_version')
    )
    
    # User MFA table (deferred implementation)
    op.create_table(
        'user_mfa',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('factor_type', sa.Enum('totp', 'webauthn', name='mfa_factor_type'), nullable=False),
        sa.Column('enrolled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('secret_hash', sa.String(length=255), nullable=True),
        sa.Column('credential_public_key', sa.LargeBinary(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'factor_type')
    )


def downgrade() -> None:
    """Drop all tables and enum types."""
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
    
    # Drop enum types (asyncpg requires separate statements)
    op.execute("DROP TYPE IF EXISTS mfa_factor_type")
    op.execute("DROP TYPE IF EXISTS decision")
    op.execute("DROP TYPE IF EXISTS flag_state")
    op.execute("DROP TYPE IF EXISTS user_status")
    op.execute("DROP TYPE IF EXISTS tenant_status")
