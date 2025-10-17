"""merge audit and user_details migrations

Revision ID: 56ba10e5592d
Revises: 94da136ac201, 5b0206f95039
Create Date: 2025-10-17 08:12:17.951381+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '56ba10e5592d'
down_revision: Union[str, None] = ('94da136ac201', '5b0206f95039')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
