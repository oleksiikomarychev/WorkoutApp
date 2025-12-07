"""add workout type index

Revision ID: c1d2e3f4a5b6
Revises: e6525343955a
Create Date: 2025-09-15 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "c1d2e3f4a5b6"
down_revision = "e6525343955a"
branch_labels = None
depends_on = None


def upgrade():
    workout_type_enum = sa.Enum("manual", "generated", name="workouttypeenum")
    workout_type_enum.create(op.get_bind(), checkfirst=True)

    op.execute("UPDATE workouts SET workout_type = 'manual' " "WHERE workout_type NOT IN ('manual', 'generated')")

    with op.batch_alter_table("workouts") as batch_op:
        batch_op.alter_column("workout_type", server_default=None)

        batch_op.alter_column(
            "workout_type",
            type_=workout_type_enum,
            existing_type=sa.VARCHAR(50),
            postgresql_using="workout_type::workouttypeenum",
            nullable=False,
            server_default="manual",
        )

    op.create_index(op.f("ix_workouts_workout_type"), "workouts", ["workout_type"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_workouts_workout_type"), table_name="workouts")

    workout_type_enum = sa.Enum("manual", "generated", name="workouttypeenum")
    with op.batch_alter_table("workouts") as batch_op:
        batch_op.alter_column("workout_type", type_=sa.VARCHAR(50), existing_type=workout_type_enum, nullable=True)
