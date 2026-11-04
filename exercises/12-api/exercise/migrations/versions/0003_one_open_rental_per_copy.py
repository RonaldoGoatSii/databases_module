"""one open rental per copy: fix the copies with two open rentals, then a partial unique index

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-04

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Data fix: for each copy with two open rentals, the older one is closed at the moment
    # the newer one started. This is data, and downgrade does NOT revert it (see README).
    op.execute(
        """
        UPDATE rental AS old
        SET return_date = newer.rental_date
        FROM rental AS newer
        WHERE old.inventory_id IN (1358, 1435, 2408)
          AND old.return_date IS NULL
          AND newer.inventory_id = old.inventory_id
          AND newer.return_date IS NULL
          AND newer.rental_date > old.rental_date
        """
    )
    op.create_index(
        "rental_one_open_per_copy",
        "rental",
        ["inventory_id"],
        unique=True,
        postgresql_where="return_date IS NULL",
    )


def downgrade() -> None:
    # Only the index is dropped. The rentals closed by the data fix stay closed.
    op.drop_index("rental_one_open_per_copy", table_name="rental")