"""add_token_replay_records_table

Revision ID: 8c01924a527d
Revises: 9f85fdd0f4d0
Create Date: 2025-10-05 04:16:44.825113+00:00

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
revision: str = '8c01924a527d'
down_revision: Union[str, None] = '9f85fdd0f4d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create token_replay_records table for replay detection (FR-SEC-020, IMPL-DB-11)
    # JTI is globally unique (single PK) to prevent superadmin token replay across tenants
    # tenant_id is optional for multi-tenant tracking
    op.create_table(
        'token_replay_records',
        sa.Column('jti', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.Float(), nullable=False),
        sa.Column('registered_at', sa.Float(), nullable=False),
        sa.Column('tenant_id', PortableUUID(), nullable=True),
        sa.PrimaryKeyConstraint('jti'),
        sa.Index('ix_token_replay_expires_at', 'expires_at'),
        sa.Index('ix_token_replay_tenant_id', 'tenant_id'),
    )


def downgrade() -> None:
    # Drop token_replay_records table
    op.drop_table('token_replay_records')
