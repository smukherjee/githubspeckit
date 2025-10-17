"""add user_details table

Revision ID: 5b0206f95039
Revises: v1_0_0_base
Create Date: 2025-10-17 06:45:48.815155+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b0206f95039'
down_revision: Union[str, None] = 'v1_0_0_base'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_details table
    op.create_table(
        'user_details',
        sa.Column('user_id', sa.UUID(), nullable=False, comment='FK to users.user_id'),
        sa.Column('full_name', sa.String(length=100), nullable=True, comment='User full name'),
        sa.Column('phone', sa.String(length=20), nullable=True, comment='Phone number (E.164 format recommended)'),
        sa.Column('address', sa.Text(), nullable=True, comment='Postal address'),
        sa.Column('photo_display_url', sa.String(length=512), nullable=True, comment='Display photo URL (640x640)'),
        sa.Column('photo_thumbnail_url', sa.String(length=512), nullable=True, comment='Thumbnail photo URL (96x96)'),
        sa.Column('photo_avatar_url', sa.String(length=512), nullable=True, comment='Avatar photo URL (48x48)'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='Record creation timestamp'),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='Record last update timestamp'),
        sa.Column('created_by', sa.UUID(), nullable=False, comment='User who created the record'),
        sa.Column('updated_by', sa.UUID(), nullable=False, comment='User who last updated the record'),
        sa.PrimaryKeyConstraint('user_id', name='pk_user_details'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], name='fk_user_details_user_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], name='fk_user_details_created_by'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.user_id'], name='fk_user_details_updated_by'),
        comment='User profile details (one-to-one with users)',
    )

    # Create indexes for audit fields
    op.create_index('ix_user_details_created_at', 'user_details', ['created_at'])
    op.create_index('ix_user_details_updated_at', 'user_details', ['updated_at'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_user_details_updated_at', table_name='user_details')
    op.drop_index('ix_user_details_created_at', table_name='user_details')
    
    # Drop table (CASCADE will handle foreign key constraints)
    op.drop_table('user_details')
