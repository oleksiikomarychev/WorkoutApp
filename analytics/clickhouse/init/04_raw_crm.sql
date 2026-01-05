-- ClickHouse: Raw таблицы для crm

-- coach_athlete_links
CREATE TABLE IF NOT EXISTS raw.coach_athlete_links
(
    id             Int32,
    coach_id       String,
    athlete_id     String,
    status         Nullable(String),
    channel_id     Nullable(String),
    note           Nullable(String),
    ended_at       Nullable(DateTime64(3)),
    ended_reason   Nullable(String),
    created_at     Nullable(DateTime64(3)),
    updated_at     Nullable(DateTime64(3)),
    __op           LowCardinality(String),
    __source_ts_ms Int64,
    _version       UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.coach_athlete_links_kafka
(
    id             Int32,
    coach_id       String,
    athlete_id     String,
    status         Nullable(String),
    channel_id     Nullable(String),
    note           Nullable(String),
    ended_at       Nullable(DateTime64(3)),
    ended_reason   Nullable(String),
    created_at     Nullable(DateTime64(3)),
    updated_at     Nullable(DateTime64(3)),
    __op           LowCardinality(String),
    __source_ts_ms Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'crm-db.public.coach_athlete_links',
    kafka_group_name = 'clickhouse_crm_coach_athlete_links',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.coach_athlete_links_mv TO raw.coach_athlete_links AS
SELECT * FROM raw.coach_athlete_links_kafka;

-- coach_athlete_events
CREATE TABLE IF NOT EXISTS raw.coach_athlete_events
(
    id             Int32,
    link_id        Int32,
    actor_id       String,
    type           Nullable(String),
    payload        Nullable(String),
    created_at     Nullable(DateTime64(3)),
    __op           LowCardinality(String),
    __source_ts_ms Int64,
    _version       UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.coach_athlete_events_kafka
(
    id             Int32,
    link_id        Int32,
    actor_id       String,
    type           Nullable(String),
    payload        Nullable(String),
    created_at     Nullable(DateTime64(3)),
    __op           LowCardinality(String),
    __source_ts_ms Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'crm-db.public.coach_athlete_events',
    kafka_group_name = 'clickhouse_crm_coach_athlete_events',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.coach_athlete_events_mv TO raw.coach_athlete_events AS
SELECT * FROM raw.coach_athlete_events_kafka;

-- coach_athlete_notes
CREATE TABLE IF NOT EXISTS raw.coach_athlete_notes
(
    id             Int32,
    link_id        Int32,
    author_id      String,
    text           Nullable(String),
    note_type      Nullable(String),
    pinned         Nullable(UInt8),
    created_at     Nullable(DateTime64(3)),
    updated_at     Nullable(DateTime64(3)),
    __op           LowCardinality(String),
    __source_ts_ms Int64,
    _version       UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.coach_athlete_notes_kafka
(
    id             Int32,
    link_id        Int32,
    author_id      String,
    text           Nullable(String),
    note_type      Nullable(String),
    pinned         Nullable(UInt8),
    created_at     Nullable(DateTime64(3)),
    updated_at     Nullable(DateTime64(3)),
    __op           LowCardinality(String),
    __source_ts_ms Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'crm-db.public.coach_athlete_notes',
    kafka_group_name = 'clickhouse_crm_coach_athlete_notes',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.coach_athlete_notes_mv TO raw.coach_athlete_notes AS
SELECT * FROM raw.coach_athlete_notes_kafka;

-- coach_athlete_tags
CREATE TABLE IF NOT EXISTS raw.coach_athlete_tags
(
    id             Int32,
    owner_id       String,
    name           Nullable(String),
    color          Nullable(String),
    is_active      Nullable(UInt8),
    is_global      Nullable(UInt8),
    created_at     Nullable(DateTime64(3)),
    updated_at     Nullable(DateTime64(3)),
    __op           LowCardinality(String),
    __source_ts_ms Int64,
    _version       UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.coach_athlete_tags_kafka
(
    id             Int32,
    owner_id       String,
    name           Nullable(String),
    color          Nullable(String),
    is_active      Nullable(UInt8),
    is_global      Nullable(UInt8),
    created_at     Nullable(DateTime64(3)),
    updated_at     Nullable(DateTime64(3)),
    __op           LowCardinality(String),
    __source_ts_ms Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'crm-db.public.coach_athlete_tags',
    kafka_group_name = 'clickhouse_crm_coach_athlete_tags',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.coach_athlete_tags_mv TO raw.coach_athlete_tags AS
SELECT * FROM raw.coach_athlete_tags_kafka;

-- coach_athlete_link_tags
CREATE TABLE IF NOT EXISTS raw.coach_athlete_link_tags
(
    id             Int32,
    link_id        Int32,
    tag_id         Int32,
    created_at     Nullable(DateTime64(3)),
    __op           LowCardinality(String),
    __source_ts_ms Int64,
    _version       UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.coach_athlete_link_tags_kafka
(
    id             Int32,
    link_id        Int32,
    tag_id         Int32,
    created_at     Nullable(DateTime64(3)),
    __op           LowCardinality(String),
    __source_ts_ms Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'crm-db.public.coach_athlete_link_tags',
    kafka_group_name = 'clickhouse_crm_coach_athlete_link_tags',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.coach_athlete_link_tags_mv TO raw.coach_athlete_link_tags AS
SELECT * FROM raw.coach_athlete_link_tags_kafka;

-- coach_athlete_payments
CREATE TABLE IF NOT EXISTS raw.coach_athlete_payments
(
    id                         Int32,
    link_id                    Int32,
    coach_id                   String,
    athlete_id                 String,
    amount_minor               Nullable(Int32),
    currency                   Nullable(String),
    status                     Nullable(String),
    stripe_checkout_session_id Nullable(String),
    stripe_payment_intent_id   Nullable(String),
    valid_until                Nullable(DateTime64(3)),
    created_at                 Nullable(DateTime64(3)),
    updated_at                 Nullable(DateTime64(3)),
    __op                       LowCardinality(String),
    __source_ts_ms             Int64,
    _version                   UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.coach_athlete_payments_kafka
(
    id                         Int32,
    link_id                    Int32,
    coach_id                   String,
    athlete_id                 String,
    amount_minor               Nullable(Int32),
    currency                   Nullable(String),
    status                     Nullable(String),
    stripe_checkout_session_id Nullable(String),
    stripe_payment_intent_id   Nullable(String),
    valid_until                Nullable(DateTime64(3)),
    created_at                 Nullable(DateTime64(3)),
    updated_at                 Nullable(DateTime64(3)),
    __op                       LowCardinality(String),
    __source_ts_ms             Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'crm-db.public.coach_athlete_payments',
    kafka_group_name = 'clickhouse_crm_coach_athlete_payments',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.coach_athlete_payments_mv TO raw.coach_athlete_payments AS
SELECT * FROM raw.coach_athlete_payments_kafka;
