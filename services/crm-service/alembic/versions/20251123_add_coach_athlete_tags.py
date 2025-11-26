import sqlalchemy as sa
from alembic import op

revision = "20251123_add_coach_athlete_tags"
down_revision = "20251123_add_coach_athlete_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coach_athlete_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("color", sa.String(length=32), nullable=True),
        sa.Column("is_global", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("owner_id", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("owner_id", "name", name="uq_coach_tags_owner_name"),
    )
    op.create_index("ix_coach_athlete_tags_active", "coach_athlete_tags", ["is_active"])

    op.create_table(
        "coach_athlete_link_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "link_id",
            sa.Integer(),
            sa.ForeignKey("coach_athlete_links.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tag_id",
            sa.Integer(),
            sa.ForeignKey("coach_athlete_tags.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("link_id", "tag_id", name="uq_link_tag"),
    )
    op.create_index(
        "ix_coach_athlete_link_tags_tag_created",
        "coach_athlete_link_tags",
        ["tag_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_coach_athlete_link_tags_tag_created", table_name="coach_athlete_link_tags")
    op.drop_table("coach_athlete_link_tags")
    op.drop_index("ix_coach_athlete_tags_active", table_name="coach_athlete_tags")
    op.drop_table("coach_athlete_tags")
