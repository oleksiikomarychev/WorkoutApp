"""Merge alembic heads

Revision ID: 8c3f4a1b2d9f
Revises: 9abcde123456, 8c3f4a1b2d9e
Create Date: 2025-12-14
"""

from collections.abc import Sequence

from alembic import op

revision: str = "8c3f4a1b2d9f"
down_revision: tuple[str, str] | None = ("9abcde123456", "8c3f4a1b2d9e")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    return


def downgrade() -> None:
    return
