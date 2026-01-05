-- ClickHouse: Raw таблицы для agent

CREATE TABLE IF NOT EXISTS raw.generated_plans
(
    id             Int32,
    user_id        String,
    plan_data      Nullable(String),
    created_at     Nullable(DateTime64(3)),
    __op           LowCardinality(String),
    __source_ts_ms Int64,
    _version       UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.generated_plans_kafka
(
    id             Int32,
    user_id        String,
    plan_data      Nullable(String),
    created_at     Nullable(DateTime64(3)),
    __op           LowCardinality(String),
    __source_ts_ms Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'agent-db.public.generated_plans',
    kafka_group_name = 'clickhouse_agent_generated_plans',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.generated_plans_mv TO raw.generated_plans AS
SELECT * FROM raw.generated_plans_kafka;
