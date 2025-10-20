"""add_schema_version_metadata_table

Revision ID: 3da4ba72b3b5
Revises: 9a6e88ad1601
Create Date: 2025-10-20 06:29:11.241647+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3da4ba72b3b5'
down_revision: Union[str, None] = '9a6e88ad1601'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create schema_version metadata table for V1.0 tracking.
    
    This table provides a human-readable version marker independent of Alembic's
    internal version tracking.
    """
    op.create_table(
        'schema_version',
        sa.Column('version', sa.String(20), primary_key=True, nullable=False),
        sa.Column(
            'applied_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP')
        ),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('checksum', sa.String(64), nullable=True),
        if_not_exists=True,
    )
    
    # Insert V1.0 marker (ignore if already exists)
    conn = op.get_bind()
    if conn.dialect.name == 'sqlite':
        op.execute(
            """
            INSERT OR IGNORE INTO schema_version (version, description)
            VALUES ('1.0.0', 'V1.0 release: Per-tenant email uniqueness, removed deprecation middleware')
            """
        )
    else:
        op.execute(
            """
            INSERT INTO schema_version (version, description)
            VALUES ('1.0.0', 'V1.0 release: Per-tenant email uniqueness, removed deprecation middleware')
            ON CONFLICT (version) DO NOTHING
            """
        )


def downgrade() -> None:
    """
    Remove schema_version metadata table.
    """
    op.drop_table('schema_version')
