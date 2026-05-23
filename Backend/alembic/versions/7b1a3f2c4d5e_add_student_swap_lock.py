"""Add student swap_lock

Revision ID: 7b1a3f2c4d5e
Revises: 5a1b6c1d2e3f
Create Date: 2026-05-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7b1a3f2c4d5e"
down_revision: Union[str, None] = "5a1b6c1d2e3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "student",
        sa.Column(
            "swap_lock",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("student", "swap_lock")
