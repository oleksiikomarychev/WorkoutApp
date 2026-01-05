-- ClickHouse: Raw таблицы для user_max

-- user_maxes
CREATE TABLE IF NOT EXISTS raw.user_maxes
(
    id             Int32,
    user_id        String,
    exercise_id    Int32,
    exercise_name  Nullable(String),
    max_weight     Nullable(Int32),
    rep_max        Nullable(Int32),
    true_1rm       Nullable(Float64),
    verified_1rm   Nullable(Float64),
    date           Nullable(Date),
    source         Nullable(String),
    __op           LowCardinality(String),
    __source_ts_ms Int64,
    _version       UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.user_maxes_kafka
(
    id             Int32,
    user_id        String,
    exercise_id    Int32,
    exercise_name  Nullable(String),
    max_weight     Nullable(Int32),
    rep_max        Nullable(Int32),
    true_1rm       Nullable(Float64),
    verified_1rm   Nullable(Float64),
    date           Nullable(Date),
    source         Nullable(String),
    __op           LowCardinality(String),
    __source_ts_ms Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'user-max-db.public.user_maxes',
    kafka_group_name = 'clickhouse_user_max_user_maxes',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.user_maxes_mv TO raw.user_maxes AS
SELECT * FROM raw.user_maxes_kafka;

-- user_max_daily_agg
CREATE TABLE IF NOT EXISTS raw.user_max_daily_agg
(
    id             Int32,
    user_id        String,
    exercise_id    Int32,
    date           Date,
    sum_true_1rm   Nullable(Float64),
    cnt            Nullable(Int32),
    __op           LowCardinality(String),
    __source_ts_ms Int64,
    _version       UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.user_max_daily_agg_kafka
(
    id             Int32,
    user_id        String,
    exercise_id    Int32,
    date           Date,
    sum_true_1rm   Nullable(Float64),
    cnt            Nullable(Int32),
    __op           LowCardinality(String),
    __source_ts_ms Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'user-max-db.public.user_max_daily_agg',
    kafka_group_name = 'clickhouse_user_max_user_max_daily_agg',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.user_max_daily_agg_mv TO raw.user_max_daily_agg AS
SELECT * FROM raw.user_max_daily_agg_kafka;
