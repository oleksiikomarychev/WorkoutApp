"""ensure display_name is not null

Revision ID: 20251123_display_name_not_null
Revises: 20251123_make_profiles_public
Create Date: 2025-11-23
"""

import sqlalchemy as sa
from alembic import op

revision = "20251123_display_name_not_null"
down_revision = "20251123_make_profiles_public"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text("""
        UPDATE user_profiles
        SET display_name = user_id
        WHERE display_name IS NULL OR display_name = ''
    """)
    )

    op.alter_column(
        "user_profiles",
        "display_name",
        existing_type=sa.String(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "user_profiles",
        "display_name",
        existing_type=sa.String(),
        nullable=True,
    )
