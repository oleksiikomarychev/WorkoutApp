-- Create outbox_events table for both social and messaging databases
CREATE TABLE IF NOT EXISTS outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_name VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    published_at TIMESTAMP WITH TIME ZONE,
    retry_count INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT check_outbox_events_retry_count CHECK (published_at IS NULL OR retry_count >= 0)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_outbox_events_stream_name ON outbox_events(stream_name);
CREATE INDEX IF NOT EXISTS idx_outbox_unpublished ON outbox_events(created_at) WHERE published_at IS NULL;
