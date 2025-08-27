"""create exercises tables and seed data

Revision ID: 0001_initial_exercises
Revises: 
Create Date: 2025-08-27 10:45:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0001_initial_exercises'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Create exercise_list table if missing
    if not insp.has_table('exercise_list'):
        op.create_table(
            'exercise_list',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('muscle_group', sa.String(length=255), nullable=True),
            sa.Column('equipment', sa.String(length=255), nullable=True),
            sa.Column('target_muscles', sa.JSON(), nullable=True),
            sa.Column('synergist_muscles', sa.JSON(), nullable=True),
            sa.Column('movement_type', sa.String(length=32), nullable=True),
            sa.Column('region', sa.String(length=32), nullable=True),
            sa.UniqueConstraint('name', name='uq_exercise_list_name'),
        )
        # Unique constraint above enforces uniqueness; SQLite will create an index for it implicitly.

    # Create exercise_instances table if missing
    if not insp.has_table('exercise_instances'):
        op.create_table(
            'exercise_instances',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('workout_id', sa.Integer(), nullable=False),
            sa.Column('exercise_list_id', sa.Integer(), nullable=False),
            sa.Column('user_max_id', sa.Integer(), nullable=True),
            sa.Column('sets', sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('order', sa.Integer(), nullable=True),
        )

    # Ensure indexes exist on exercise_instances
    existing_ix = {ix['name'] for ix in insp.get_indexes('exercise_instances')} if insp.has_table('exercise_instances') else set()
    if 'ix_exercise_instances_exercise_list_id' not in existing_ix and insp.has_table('exercise_instances'):
        op.create_index('ix_exercise_instances_exercise_list_id', 'exercise_instances', ['exercise_list_id'])
    if 'ix_exercise_instances_workout_id' not in existing_ix and insp.has_table('exercise_instances'):
        op.create_index('ix_exercise_instances_workout_id', 'exercise_instances', ['workout_id'])

    # Seed minimal exercise definitions only if table exists and is empty
    if insp.has_table('exercise_list'):
        conn = bind
        meta = sa.MetaData()
        exercise_list_table = sa.Table('exercise_list', meta, autoload_with=conn)
        count = conn.execute(sa.select(sa.func.count()).select_from(exercise_list_table)).scalar_one()
        if count == 0:
            op.bulk_insert(
                exercise_list_table,
                [
                    {
                        'name': 'Back Squat',
                        'muscle_group': 'legs',
                        'equipment': 'barbell',
                        'target_muscles': ['quadriceps', 'glutes'],
                        'synergist_muscles': ['hamstrings', 'erectors'],
                        'movement_type': 'compound',
                        'region': 'lower',
                    },
                    {
                        'name': 'Bench Press',
                        'muscle_group': 'chest',
                        'equipment': 'barbell',
                        'target_muscles': ['pectoralis major'],
                        'synergist_muscles': ['triceps', 'anterior deltoid'],
                        'movement_type': 'compound',
                        'region': 'upper',
                    },
                    {
                        'name': 'Deadlift',
                        'muscle_group': 'back',
                        'equipment': 'barbell',
                        'target_muscles': ['erectors', 'glutes', 'hamstrings'],
                        'synergist_muscles': ['forearms', 'lats'],
                        'movement_type': 'compound',
                        'region': 'lower',
                    },
                ],
            )


def downgrade() -> None:
    op.drop_index('ix_exercise_instances_workout_id', table_name='exercise_instances')
    op.drop_index('ix_exercise_instances_exercise_list_id', table_name='exercise_instances')
    op.drop_table('exercise_instances')

    op.drop_table('exercise_list')
