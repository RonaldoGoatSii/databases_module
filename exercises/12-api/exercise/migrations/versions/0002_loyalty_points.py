"""add customer.loyalty_points, filled with the number of rentals

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. add the column as nullable, so that existing rows are allowed
    op.add_column("customer", sa.Column("loyalty_points", sa.Integer(), nullable=True))
    # 2. fill it with the number of rentals of each customer
    op.execute(
        """
        UPDATE customer c
        SET loyalty_points = (SELECT count(*) FROM rental r WHERE r.customer_id = c.customer_id)
        """
    )
    # 3. make it NOT NULL, with 0 as default for new rows
    op.alter_column("customer", "loyalty_points", nullable=False, server_default="0")


def downgrade() -> None:
    op.drop_column("customer", "loyalty_points")