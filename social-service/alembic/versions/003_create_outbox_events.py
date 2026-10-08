"""Create outbox_events table

Revision ID: 003_create_outbox_events
Revises: 002_add_webhook_subscriptions
Create Date: 2026-04-02 23:48:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_create_outbox_events'
down_revision: str | None = '57ea359615fc'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create outbox_events table
    op.create_table('outbox_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stream_name', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('published_at IS NULL OR retry_count >= 0', name='check_outbox_events_retry_count')
    )
    op.create_index('idx_outbox_unpublished', 'outbox_events', ['created_at'], unique=False, postgresql_where=sa.text('published_at IS NULL'))
    op.create_index('idx_outbox_events_stream_name', 'outbox_events', ['stream_name'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_outbox_events_stream_name', table_name='outbox_events')
    op.drop_table('outbox_events')
