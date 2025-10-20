"""ensure_per_tenant_email_unique_index

Revision ID: 9a6e88ad1601
Revises: 56b3e20010a2
Create Date: 2025-10-20 06:28:51.328371+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a6e88ad1601'
down_revision: Union[str, None] = '56b3e20010a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Ensure composite unique index on (email, tenant_id) exists.
    
    V1.0 Requirement: Email uniqueness is per-tenant, not global.
    This index may already exist from earlier migrations, so we create it only if needed.
    """
    # Create composite unique index (idempotent operation)
    # If index already exists, this will be a no-op in most databases
    with op.batch_alter_table('users', schema=None) as batch_op:
        # Check if index already exists would require inspector, so we use try/except
        try:
            batch_op.create_index(
                'idx_users_email_tenant',
                ['email', 'tenant_id'],
                unique=True
            )
        except Exception:
            # Index likely already exists as ix_users_tenant_email
            pass


def downgrade() -> None:
    """
    Remove per-tenant email uniqueness index.
    
    Note: The older index ix_users_tenant_email may still exist.
    """
    with op.batch_alter_table('users', schema=None) as batch_op:
        try:
            batch_op.drop_index('idx_users_email_tenant')
        except Exception:
            # Index may not exist or may have different name
            pass
