"""Add swap request active pair index

Revision ID: 5a1b6c1d2e3f
Revises: 319ccba38e49
Create Date: 2026-05-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5a1b6c1d2e3f"
down_revision: Union[str, None] = "319ccba38e49"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_swap_request_active_pair",
        "swap_request",
        [
            sa.text("LEAST(requester_assignment_id, target_assignment_id)"),
            sa.text("GREATEST(requester_assignment_id, target_assignment_id)"),
        ],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING','ACCEPTED')"),
    )


def downgrade() -> None:
    op.drop_index("uq_swap_request_active_pair", table_name="swap_request")
