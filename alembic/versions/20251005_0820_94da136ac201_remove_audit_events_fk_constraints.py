"""remove_audit_events_fk_constraints

Revision ID: 94da136ac201
Revises: 8c01924a527d
Create Date: 2025-10-05 08:20:35.841783+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94da136ac201'
down_revision: Union[str, None] = '8c01924a527d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove FK constraints from audit_events table.
    
    Rationale: Audit tables should not have FK constraints to ensure
    historical records are never blocked. Application layer handles
    referential integrity.
    """
    # Drop existing foreign key constraints
    op.drop_constraint('audit_events_tenant_id_fkey', 'audit_events', type_='foreignkey')
    op.drop_constraint('audit_events_actor_user_id_fkey', 'audit_events', type_='foreignkey')


def downgrade() -> None:
    """Restore FK constraints to audit_events table."""
    # Recreate foreign key constraints (NO ACTION by default)
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
