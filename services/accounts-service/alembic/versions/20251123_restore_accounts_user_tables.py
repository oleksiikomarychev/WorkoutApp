"""accounts: restore core user tables if missing

This migration is intended for development environments where an autogen
migration accidentally dropped core user tables (user_profiles,
user_settings, user_avatars, user_coaching_profiles). It recreates them
if they are missing, matching the current SQLAlchemy models.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision = "20251123_restore_accounts"
down_revision = "8b57bf954ef7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = 'unitsystem'
                ) THEN
                    CREATE TYPE unitsystem AS ENUM ('metric', 'imperial');
                END IF;
            END;
            $$;
            """
        )
    )

    if "user_profiles" not in tables:
        op.create_table(
            "user_profiles",
            sa.Column("user_id", sa.String(), primary_key=True),
            sa.Column("display_name", sa.String(), nullable=False),
            sa.Column("bio", sa.String(), nullable=True),
            sa.Column("photo_url", sa.String(), nullable=True),
            sa.Column("bodyweight_kg", sa.Float(), nullable=True),
            sa.Column("height_cm", sa.Float(), nullable=True),
            sa.Column("age", sa.Integer(), nullable=True),
            sa.Column("sex", sa.String(length=16), nullable=True),
            sa.Column("training_experience_years", sa.Float(), nullable=True),
            sa.Column("training_experience_level", sa.String(length=32), nullable=True),
            sa.Column("primary_default_goal", sa.String(length=32), nullable=True),
            sa.Column("training_environment", sa.String(length=32), nullable=True),
            sa.Column("weekly_gain_coef", sa.Float(), nullable=True),
            sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_public", sa.Boolean(), nullable=False, server_default=text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )

    if "user_avatars" not in tables:
        op.create_table(
            "user_avatars",
            sa.Column("user_id", sa.String(), primary_key=True),
            sa.Column("content_type", sa.String(length=64), nullable=False, server_default="image/png"),
            sa.Column("image", sa.LargeBinary(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )

    if "user_settings" not in tables:
        unit_system_enum = postgresql.ENUM(
            "metric",
            "imperial",
            name="unitsystem",
            create_type=False,
        )

        op.create_table(
            "user_settings",
            sa.Column(
                "user_id",
                sa.String(),
                sa.ForeignKey("user_profiles.user_id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "unit_system",
                unit_system_enum,
                nullable=False,
                server_default="metric",
            ),
            sa.Column("locale", sa.String(), nullable=False, server_default="en"),
            sa.Column("timezone", sa.String(), nullable=True),
            sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )

    if "user_coaching_profiles" not in tables:
        op.create_table(
            "user_coaching_profiles",
            sa.Column(
                "user_id",
                sa.String(),
                sa.ForeignKey("user_profiles.user_id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=text("false")),
            sa.Column("accepting_clients", sa.Boolean(), nullable=False, server_default=text("false")),
            sa.Column("tagline", sa.String(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "specializations",
                sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=text("'[]'::jsonb"),
            ),
            sa.Column(
                "languages",
                sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=text("'[]'::jsonb"),
            ),
            sa.Column("experience_years", sa.Integer(), nullable=True),
            sa.Column("timezone", sa.String(), nullable=True),
            sa.Column("rate_type", sa.String(length=32), nullable=True),
            sa.Column("rate_currency", sa.String(length=3), nullable=True),
            sa.Column("rate_amount_minor", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    """Downgrade is intentionally lossy and only drops tables if present.

    This is for development recovery only.
    """
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    for name in ["user_coaching_profiles", "user_settings", "user_avatars", "user_profiles"]:
        if name in tables:
            op.drop_table(name)
