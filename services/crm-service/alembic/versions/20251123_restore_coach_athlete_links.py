"""crm: restore coach_athlete_links table and indexes if missing

Used to recover from a previous autogen migration that may have dropped the
coach_athlete_links table in development environments.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "20251123_crm_restore_links"
down_revision = "d59950afde1b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "coach_athlete_links" not in tables:
        op.create_table(
            "coach_athlete_links",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("coach_id", sa.String(length=255), nullable=False),
            sa.Column("athlete_id", sa.String(length=255), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("channel_id", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ended_reason", sa.Text(), nullable=True),
            sa.UniqueConstraint("coach_id", "athlete_id", name="uq_coach_athlete_pair"),
        )

        op.create_index("ix_coach_athlete_links_id", "coach_athlete_links", ["id"], unique=False)
        op.create_index("ix_coach_athlete_links_coach_id", "coach_athlete_links", ["coach_id"], unique=False)
        op.create_index("ix_coach_athlete_links_athlete_id", "coach_athlete_links", ["athlete_id"], unique=False)
        op.create_index("ix_coach_athlete_links_status", "coach_athlete_links", ["status"], unique=False)
        op.create_index("ix_coach_status", "coach_athlete_links", ["coach_id", "status"], unique=False)
        op.create_index("ix_athlete_status", "coach_athlete_links", ["athlete_id", "status"], unique=False)
        op.create_index("ix_coach_athlete_channel", "coach_athlete_links", ["channel_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "coach_athlete_links" in tables:
        op.drop_table("coach_athlete_links")
