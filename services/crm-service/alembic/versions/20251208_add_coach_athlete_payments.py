"""add coach athlete payments table

Revision ID: 20251208_add_payments
Revises: 20251123_add_coach_athlete_tags
Create Date: 2025-12-08
"""

import sqlalchemy as sa
from alembic import op

revision = "20251208_add_payments"
down_revision = "20251123_add_coach_athlete_tags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coach_athlete_payments",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("stripe_checkout_session_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_payment_intent_id", sa.String(length=255), nullable=True),
        sa.Column("coach_id", sa.String(length=255), nullable=False),
        sa.Column("athlete_id", sa.String(length=255), nullable=False),
        sa.Column("link_id", sa.Integer, sa.ForeignKey("coach_athlete_links.id", ondelete="SET NULL"), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("amount_minor", sa.Integer, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_payments_checkout_session_id",
        "coach_athlete_payments",
        ["stripe_checkout_session_id"],
        unique=True,
    )
    op.create_index(
        "ix_payments_payment_intent_id",
        "coach_athlete_payments",
        ["stripe_payment_intent_id"],
        unique=True,
    )
    op.create_index(
        "ix_payments_coach_id",
        "coach_athlete_payments",
        ["coach_id"],
        unique=False,
    )
    op.create_index(
        "ix_payments_athlete_id",
        "coach_athlete_payments",
        ["athlete_id"],
        unique=False,
    )
    op.create_index(
        "ix_payments_link_id",
        "coach_athlete_payments",
        ["link_id"],
        unique=False,
    )
    op.create_index(
        "ix_payments_status",
        "coach_athlete_payments",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_payments_status", table_name="coach_athlete_payments")
    op.drop_index("ix_payments_link_id", table_name="coach_athlete_payments")
    op.drop_index("ix_payments_athlete_id", table_name="coach_athlete_payments")
    op.drop_index("ix_payments_coach_id", table_name="coach_athlete_payments")
    op.drop_index("ix_payments_payment_intent_id", table_name="coach_athlete_payments")
    op.drop_index("ix_payments_checkout_session_id", table_name="coach_athlete_payments")
    op.drop_table("coach_athlete_payments")
