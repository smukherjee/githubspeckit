"""fix_audit_events_fk_set_null

Revision ID: 81dc1f90f26f
Revises: 8c01924a527d
Create Date: 2025-10-05 08:16:15.432028+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '81dc1f90f26f'
down_revision: Union[str, None] = '8c01924a527d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix audit_events foreign key constraints to use SET NULL on delete."""
    # Drop existing foreign key constraints
    op.drop_constraint('audit_events_tenant_id_fkey', 'audit_events', type_='foreignkey')
    op.drop_constraint('audit_events_actor_user_id_fkey', 'audit_events', type_='foreignkey')
    
    # Recreate with correct ondelete behavior
    op.create_foreign_key(
        'audit_events_tenant_id_fkey',
        'audit_events',
        'tenants',
        ['tenant_id'],
        ['tenant_id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'audit_events_actor_user_id_fkey',
        'audit_events',
        'users',
        ['actor_user_id'],
        ['user_id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Revert to NO ACTION foreign key constraints."""
    # Drop SET NULL constraints
    op.drop_constraint('audit_events_tenant_id_fkey', 'audit_events', type_='foreignkey')
    op.drop_constraint('audit_events_actor_user_id_fkey', 'audit_events', type_='foreignkey')
    
    # Recreate with NO ACTION (default)
    op.create_foreign_key(
        'audit_events_tenant_id_fkey',
        'audit_events',
        'tenants',
        ['tenant_id'],
        ['tenant_id']
    )
    op.create_foreign_key(
        'audit_events_actor_user_id_fkey',
        'audit_events',
        'users',
        ['actor_user_id'],
        ['user_id']
    )
