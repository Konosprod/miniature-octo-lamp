"""add anime_id index

Revision ID: 3a18cf65470b
Revises: 7837b77e53fe
Create Date: 2026-09-22 16:16:45.949722

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a18cf65470b'
down_revision: Union[str, None] = '7837b77e53fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_anime_anime_id", "anime", ["anime_id"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_anime_anime_id", table_name="anime")
