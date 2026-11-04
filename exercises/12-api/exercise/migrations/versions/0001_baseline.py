"""baseline: the schema that already exists in Pagila (nothing to change)

Revision ID: 0001
Revises:
Create Date: 2026-11-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Empty on purpose: the tables already exist. Run `alembic stamp 0001` on a database
    # created from Pagila, so that Alembic starts tracking from here.
    pass


def downgrade() -> None:
    pass