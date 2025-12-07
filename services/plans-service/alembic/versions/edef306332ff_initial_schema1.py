"""initial_schema1

Revision ID: edef306332ff
Revises: e4e18296237c
Create Date: 2025-09-17 00:35:01.406338
"""

import sqlalchemy as sa
from alembic import op

revision = "edef306332ff"
down_revision = "e4e18296237c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "workouts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("microcycle_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("day", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["microcycle_id"], ["microcycles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workouts_id"), "workouts", ["id"], unique=False)
    op.create_table(
        "workout_exercises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workout_id", sa.Integer(), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["workout_id"], ["workouts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workout_exercises_id"), "workout_exercises", ["id"], unique=False)
    op.create_table(
        "workout_exercise_sets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workout_exercise_id", sa.Integer(), nullable=False),
        sa.Column("intensity", sa.Integer(), nullable=True),
        sa.Column("effort", sa.Float(), nullable=True),
        sa.Column("volume", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["workout_exercise_id"], ["workout_exercises.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workout_exercise_sets_id"), "workout_exercise_sets", ["id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_workout_exercise_sets_id"), table_name="workout_exercise_sets")
    op.drop_table("workout_exercise_sets")
    op.drop_index(op.f("ix_workout_exercises_id"), table_name="workout_exercises")
    op.drop_table("workout_exercises")
    op.drop_index(op.f("ix_workouts_id"), table_name="workouts")
    op.drop_table("workouts")
