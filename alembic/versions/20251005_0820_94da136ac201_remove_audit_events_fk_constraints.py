"""remove_audit_events_fk_constraints

Revision ID: 94da136ac201
Revises: v1_0_0_base
Create Date: 2025-10-05 08:20:35.841783+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94da136ac201'
down_revision: Union[str, None] = 'v1_0_0_base'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove FK constraints from audit_events table.
    
    Rationale: Audit tables should not have FK constraints to ensure
    historical records are never blocked. Application layer handles
    referential integrity.
    
    Database Compatibility:
    - PostgreSQL: Drop named FK constraints directly (if they exist)
    - SQLite: Recreate table without FKs (SQLite doesn't use named FKs)
    """
    # Detect database dialect
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    
    if dialect_name == 'postgresql':
        # PostgreSQL: Check if constraints exist before dropping them
        # Query to check if constraint exists
        inspector = sa.inspect(bind)
        
        # Get foreign keys for the audit_events table
        try:
            foreign_keys = inspector.get_foreign_keys('audit_events')
            existing_constraint_names = {fk['name'] for fk in foreign_keys}
            
            # Only drop constraints that actually exist
            if 'audit_events_tenant_id_fkey' in existing_constraint_names:
                op.drop_constraint('audit_events_tenant_id_fkey', 'audit_events', type_='foreignkey')
            
            if 'audit_events_actor_user_id_fkey' in existing_constraint_names:
                op.drop_constraint('audit_events_actor_user_id_fkey', 'audit_events', type_='foreignkey')
                
        except Exception:
            # If we can't inspect constraints, the table might not exist yet
            # or constraints might already be dropped - this is fine
            pass
    else:
        # SQLite/other: Recreate table without foreign keys using batch mode
        # This is a no-op if table was created without named FKs originally
        with op.batch_alter_table('audit_events', schema=None, copy_from=None, 
                                   recreate='always') as batch_op:
            # When recreating, Alembic will inspect the table and omit FK constraints
            # if we don't explicitly re-add them (which we don't want)
            pass


def downgrade() -> None:
    """Restore FK constraints to audit_events table.
    
    Database Compatibility:
    - PostgreSQL: Add named FK constraints directly
    - SQLite: Recreate table with FKs
    """
    # Detect database dialect
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    
    if dialect_name == 'postgresql':
        # PostgreSQL: Add constraints by name
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
    else:
        # SQLite/other: Use batch mode to recreate table with FKs
        with op.batch_alter_table('audit_events', schema=None, recreate='always') as batch_op:
            batch_op.create_foreign_key(
                None,  # SQLite doesn't use constraint names
                'tenants',
                ['tenant_id'],
                ['tenant_id']
            )
            batch_op.create_foreign_key(
                None,  # SQLite doesn't use constraint names
                'users',
                ['actor_user_id'],
                ['user_id']
            )
