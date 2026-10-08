"""Initial schema for messaging service

Revision ID: 001
Revises: 
Create Date: 2025-11-07 10:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create channels table
    op.create_table(
        'channels',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint("type IN ('direct', 'group')", name='channels_type_check'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_channels_type', 'channels', ['type'])
    
    # Create channel_members table
    op.create_table(
        'channel_members',
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('joined_at', sa.DateTime(), nullable=False),
        sa.Column('left_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('channel_id', 'user_id')
    )
    op.create_index(
        'idx_channel_members_user', 
        'channel_members', 
        ['user_id', 'joined_at'],
        postgresql_where=sa.text('left_at IS NULL')
    )
    
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('reply_to', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('attachments', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint("kind IN ('text', 'media', 'system')", name='messages_kind_check'),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reply_to'], ['messages.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_messages_channel_id', 'messages', ['channel_id'])
    op.create_index('idx_messages_sender_id', 'messages', ['sender_id'])
    op.create_index('idx_messages_created_at', 'messages', ['created_at'])
    op.create_index(
        'idx_messages_channel_created', 
        'messages', 
        ['channel_id', 'created_at'],
        postgresql_where=sa.text('deleted_at IS NULL')
    )
    
    # Create message_acknowledgments table
    op.create_table(
        'message_acknowledgments',
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('delivered', 'read')", name='message_acknowledgments_status_check'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('message_id', 'user_id', 'status')
    )
    op.create_index('idx_acks_message', 'message_acknowledgments', ['message_id', 'status'])
    
    # Create idempotency_keys table
    op.create_table(
        'idempotency_keys',
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('service', sa.String(length=50), nullable=False),
        sa.Column('endpoint', sa.String(length=255), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('response_status', sa.Integer(), nullable=False),
        sa.Column('response_body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('key')
    )
    op.create_index('idx_idempotency_created', 'idempotency_keys', ['created_at'])
    
    # Create outbox_events table
    op.create_table(
        'outbox_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stream_name', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_outbox_stream_name', 'outbox_events', ['stream_name'])
    op.create_index('idx_outbox_created_at', 'outbox_events', ['created_at'])
    op.create_index(
        'idx_outbox_unpublished', 
        'outbox_events', 
        ['created_at'],
        postgresql_where=sa.text('published_at IS NULL')
    )


def downgrade() -> None:
    op.drop_table('outbox_events')
    op.drop_table('idempotency_keys')
    op.drop_table('message_acknowledgments')
    op.drop_table('messages')
    op.drop_table('channel_members')
    op.drop_table('channels')
