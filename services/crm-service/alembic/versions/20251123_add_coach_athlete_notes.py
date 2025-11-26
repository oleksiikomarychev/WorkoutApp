import sqlalchemy as sa
from alembic import op

revision = "20251123_add_coach_athlete_notes"
down_revision = "20251123_add_ca_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coach_athlete_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("link_id", sa.Integer(), sa.ForeignKey("coach_athlete_links.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.String(length=255), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("note_type", sa.String(length=64), nullable=True),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index(
        "ix_coach_athlete_notes_link_created",
        "coach_athlete_notes",
        ["link_id", "created_at"],
    )
    op.create_index(
        "ix_coach_athlete_notes_author_created",
        "coach_athlete_notes",
        ["author_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_coach_athlete_notes_author_created", table_name="coach_athlete_notes")
    op.drop_index("ix_coach_athlete_notes_link_created", table_name="coach_athlete_notes")
    op.drop_table("coach_athlete_notes")
