"""add channel id to coach athlete links"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251123_add_channel_id"
down_revision = "20251122_init_crm_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "coach_athlete_links",
        sa.Column("channel_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_coach_athlete_channel",
        "coach_athlete_links",
        ["channel_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_coach_athlete_channel", table_name="coach_athlete_links")
    op.drop_column("coach_athlete_links", "channel_id")
