"""Create ParamsWorkout table and update Microcycle"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "1234abcd5678"
down_revision = "7bbaddb6e0d7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "params_workouts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("parameters", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.drop_column("microcycles", "schedule")

    op.add_column(
        "microcycles",
        sa.Column("params_workout_ids", postgresql.ARRAY(sa.Integer()), nullable=True),
    )


def downgrade():
    op.drop_column("microcycles", "params_workout_ids")

    op.add_column("microcycles", sa.Column("schedule", postgresql.JSONB(), nullable=True))

    op.drop_table("params_workouts")
