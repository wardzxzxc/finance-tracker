"""add color to payment_methods

Revision ID: b033d43e44fa
Revises: 45e8d0905b65
Create Date: 2026-03-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b033d43e44fa"
down_revision: Union[str, None] = "45e8d0905b65"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payment_methods",
        sa.Column("color", sa.String(7), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payment_methods", "color")
