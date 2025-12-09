"""add is_public to calendar_plans"""

import sqlalchemy as sa
from alembic import op

# NOTE: replace 'f015b8b5c1f1' with the actual latest revision id if different
revision = "add_is_public_to_calendar_plans"
down_revision = "f015b8b5c1f1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "calendar_plans",
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade():
    op.drop_column("calendar_plans", "is_public")
