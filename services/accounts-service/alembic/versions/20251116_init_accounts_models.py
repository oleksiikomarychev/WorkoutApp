"""Init accounts models: user_profiles, user_settings, user_avatars

Revision ID: 20251116_init_accounts_models
Revises: 1ae2cdd8f152
Create Date: 2025-11-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20251116_init_accounts_models"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enum for unit system, aligned with accounts_service.models.UnitSystem
    # Use a DO block with IF NOT EXISTS to avoid duplicate type errors if
    # the enum was created manually or by a previous attempt.
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

    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(), primary_key=True, index=True),
        sa.Column("display_name", sa.String(), nullable=True),
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
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "user_avatars",
        sa.Column("user_id", sa.String(), primary_key=True, index=True),
        sa.Column(
            "content_type", sa.String(length=64), nullable=False, server_default="image/png"
        ),
        sa.Column("image", sa.LargeBinary(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

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
        sa.Column(
            "notifications_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("user_settings")
    op.drop_table("user_avatars")
    op.drop_table("user_profiles")
    unit_system_enum = sa.Enum("metric", "imperial", name="unitsystem")
    unit_system_enum.drop(op.get_bind(), checkfirst=True)
