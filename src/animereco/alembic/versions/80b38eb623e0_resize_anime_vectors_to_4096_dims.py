"""resize anime vectors to 4096 dims

Revision ID: 80b38eb623e0
Revises: 3a18cf65470b
Create Date: 2026-09-22 16:31:23.574007

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80b38eb623e0'
down_revision: Union[str, None] = '3a18cf65470b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE anime ALTER COLUMN vectors TYPE vector(4096)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE anime ALTER COLUMN vectors TYPE vector(3584)")
