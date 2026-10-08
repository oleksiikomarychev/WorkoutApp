"""Add firebase_uid to posts

Revision ID: 004
Revises: 003_create_outbox_events
Create Date: 2026-04-22 08:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: str | None = '003_create_outbox_events'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add firebase_uid column to posts table
    op.add_column('posts', sa.Column('firebase_uid', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_posts_firebase_uid'), 'posts', ['firebase_uid'], unique=False)


def downgrade() -> None:
    # Remove firebase_uid column from posts table
    op.drop_index(op.f('ix_posts_firebase_uid'), table_name='posts')
    op.drop_column('posts', 'firebase_uid')
