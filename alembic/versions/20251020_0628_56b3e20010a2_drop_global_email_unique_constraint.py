"""drop_global_email_unique_constraint

Revision ID: 56b3e20010a2
Revises: 3df50b046835
Create Date: 2025-10-20 06:28:25.448097+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '56b3e20010a2'
down_revision: Union[str, None] = '3df50b046835'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Drop global email unique constraint if it exists.
    
    V1.0 Change: Email uniqueness is now per-tenant via composite index.
    The composite index ix_users_tenant_email already exists from earlier migrations.
    """
    # Check database dialect
    conn = op.get_bind()
    if conn.dialect.name == 'sqlite':
        # SQLite doesn't have named constraints in the same way
        # The composite index ix_users_tenant_email already handles uniqueness
        pass
    else:
        # PostgreSQL: drop named constraints if they exist
        op.drop_constraint('users_email_key', 'users', type_='unique', if_exists=True)
        op.drop_constraint('uq_users_email', 'users', type_='unique', if_exists=True)


def downgrade() -> None:
    """
    Restore global email unique constraint.
    
    WARNING: This may fail if duplicate emails exist across different tenants.
    In V1.0, this is expected and acceptable behavior.
    """
    conn = op.get_bind()
    if conn.dialect.name == 'sqlite':
        # SQLite: no action needed
        pass
    else:
        # PostgreSQL: recreate constraint (may fail with duplicate emails)
        op.create_unique_constraint('users_email_key', 'users', ['email'])
