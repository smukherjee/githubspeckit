"""rename_tenant_soft_deleted_to_disabled

Revision ID: 3df50b046835
Revises: 824535e758b7
Create Date: 2025-10-18 13:06:12.235747+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3df50b046835'
down_revision: Union[str, None] = '824535e758b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename tenant status 'soft_deleted' to 'disabled' for consistency.
    
    For PostgreSQL, enum values must be added outside of a transaction block.
    """
    connection = op.get_bind()
    
    # For PostgreSQL: Add new enum value outside transaction
    if connection.dialect.name == 'postgresql':
        # Execute outside of transaction using Alembic's execute with execution_options
        op.execute(
            "ALTER TYPE tenant_status ADD VALUE IF NOT EXISTS 'disabled'",
        )
        # Separate transaction to ensure enum value is committed
        connection.execute(sa.text("COMMIT"))
        connection.execute(sa.text("BEGIN"))
    
    # Update existing records (works for both SQLite and PostgreSQL)
    op.execute("UPDATE tenants SET status = 'disabled' WHERE status = 'soft_deleted'")


def downgrade() -> None:
    """Rollback: Rename tenant status 'disabled' back to 'soft_deleted'."""
    op.execute("UPDATE tenants SET status = 'soft_deleted' WHERE status = 'disabled'")
