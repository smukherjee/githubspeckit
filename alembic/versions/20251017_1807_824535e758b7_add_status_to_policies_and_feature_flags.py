"""add_status_to_policies_and_feature_flags

Revision ID: 824535e758b7
Revises: 56ba10e5592d
Create Date: 2025-10-17 18:07:13.549502+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '824535e758b7'
down_revision: Union[str, None] = '56ba10e5592d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add status column to policies table
    op.add_column('policies', sa.Column('status', sa.String(length=20), nullable=False, server_default='active'))
    
    # Add status column to feature_flags table
    op.add_column('feature_flags', sa.Column('status', sa.String(length=20), nullable=False, server_default='active'))
    
    # Create indexes for efficient filtering
    op.create_index('ix_policies_status', 'policies', ['status'])
    op.create_index('ix_feature_flags_status', 'feature_flags', ['status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_feature_flags_status', table_name='feature_flags')
    op.drop_index('ix_policies_status', table_name='policies')
    
    # Drop status columns
    op.drop_column('feature_flags', 'status')
    op.drop_column('policies', 'status')
