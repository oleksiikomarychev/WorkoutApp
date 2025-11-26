import sqlalchemy as sa
from alembic import op

revision = "20251123_add_ca_events"
down_revision = "20251123_add_note_to_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coach_athlete_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("link_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=True),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index(
        "ix_coach_athlete_events_link_created",
        "coach_athlete_events",
        ["link_id", "created_at"],
    )
    op.create_index(
        "ix_coach_athlete_events_type_created",
        "coach_athlete_events",
        ["type", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_coach_athlete_events_type_created", table_name="coach_athlete_events")
    op.drop_index("ix_coach_athlete_events_link_created", table_name="coach_athlete_events")
    op.drop_table("coach_athlete_events")
