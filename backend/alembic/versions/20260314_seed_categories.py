"""seed default categories

Revision ID: c1a2b3d4e5f6
Revises: b033d43e44fa
Create Date: 2026-03-14

"""

from typing import Sequence, Union

from alembic import op

revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, None] = "b033d43e44fa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO categories (name, color)
        VALUES
            ('Food & Drinks',     '#ff9e64'),
            ('Groceries',         '#9ece6a'),
            ('Transport',         '#7aa2f7'),
            ('Shopping',          '#f7768e'),
            ('Entertainment',     '#bb9af7'),
            ('Bills & Utilities', '#73daca'),
            ('Health & Fitness',  '#3ddc84'),
            ('Travel',            '#2ac3de'),
            ('Education',         '#e0af68'),
            ('Personal Care',     '#f9a8d4'),
            ('Subscriptions',     '#c0caf5'),
            ('Other',             '#565f89')
        ON CONFLICT (name) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM categories
        WHERE name IN (
            'Food & Dining', 'Groceries', 'Transport', 'Shopping',
            'Entertainment', 'Bills & Utilities', 'Health & Fitness',
            'Travel', 'Education', 'Personal Care', 'Subscriptions', 'Other'
        )
        """
    )
