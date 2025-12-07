"""init crm models"""

import sqlalchemy as sa
from alembic import op

revision = "20251122_init_crm_models"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coach_athlete_links",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("coach_id", sa.String(length=255), nullable=False, index=True),
        sa.Column("athlete_id", sa.String(length=255), nullable=False, index=True),
        sa.Column("status", sa.String(length=32), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_reason", sa.Text, nullable=True),
        sa.UniqueConstraint("coach_id", "athlete_id", name="uq_coach_athlete_pair"),
    )
    op.create_index("ix_coach_status", "coach_athlete_links", ["coach_id", "status"])
    op.create_index("ix_athlete_status", "coach_athlete_links", ["athlete_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_athlete_status", table_name="coach_athlete_links")
    op.drop_index("ix_coach_status", table_name="coach_athlete_links")
    op.drop_table("coach_athlete_links")
