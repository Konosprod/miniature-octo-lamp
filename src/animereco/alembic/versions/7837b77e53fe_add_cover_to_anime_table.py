"""add cover to anime table

Revision ID: 7837b77e53fe
Revises: 36980a959640
Create Date: 2026-09-22 14:38:14.121056

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7837b77e53fe'
down_revision: Union[str, None] = '36980a959640'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('anime', sa.Column('cover', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('anime', 'cover')
