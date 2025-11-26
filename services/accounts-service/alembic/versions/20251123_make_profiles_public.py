"""make all profiles public by default

Revision ID: 20251123_make_profiles_public
Revises: 20251122_add_coaching_profiles
Create Date: 2025-11-23
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251123_make_profiles_public"
down_revision = "20251122_add_coaching_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure all existing profiles are public
    op.execute(sa.text("UPDATE user_profiles SET is_public = TRUE WHERE is_public = FALSE"))
    # Set default to true for future rows
    op.alter_column(
        "user_profiles",
        "is_public",
        server_default=sa.text("true"),
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Revert default to false (data change is lossy but aligns with previous behavior)
    op.alter_column(
        "user_profiles",
        "is_public",
        server_default=sa.text("false"),
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )
    op.execute(sa.text("UPDATE user_profiles SET is_public = FALSE"))
