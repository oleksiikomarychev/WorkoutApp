-- ClickHouse: Raw таблицы для exercises

-- exercise_list
CREATE TABLE IF NOT EXISTS raw.exercise_list
(
    id               Int32,
    name             String,
    muscle_group     Nullable(String),
    equipment        Nullable(String),
    movement_type    Nullable(String),
    region           Nullable(String),
    root_exercise_id Nullable(Int32),
    target_muscles   Nullable(String),
    synergist_muscles Nullable(String),
    __op             LowCardinality(String),
    __source_ts_ms   Int64,
    _version         UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.exercise_list_kafka
(
    id               Int32,
    name             String,
    muscle_group     Nullable(String),
    equipment        Nullable(String),
    movement_type    Nullable(String),
    region           Nullable(String),
    root_exercise_id Nullable(Int32),
    target_muscles   Nullable(String),
    synergist_muscles Nullable(String),
    __op             LowCardinality(String),
    __source_ts_ms   Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'exercises-db.public.exercise_list',
    kafka_group_name = 'clickhouse_exercises_exercise_list',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.exercise_list_mv TO raw.exercise_list AS
SELECT * FROM raw.exercise_list_kafka;

-- exercise_instances
CREATE TABLE IF NOT EXISTS raw.exercise_instances
(
    id              Int32,
    workout_id      Int32,
    exercise_list_id Int32,
    user_id         String,
    user_max_id     Nullable(Int32),
    `order`         Nullable(Int32),
    sets            Nullable(String),
    notes           Nullable(String),
    __op            LowCardinality(String),
    __source_ts_ms  Int64,
    _version        UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.exercise_instances_kafka
(
    id              Int32,
    workout_id      Int32,
    exercise_list_id Int32,
    user_id         String,
    user_max_id     Nullable(Int32),
    `order`         Nullable(Int32),
    sets            Nullable(String),
    notes           Nullable(String),
    __op            LowCardinality(String),
    __source_ts_ms  Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'exercises-db.public.exercise_instances',
    kafka_group_name = 'clickhouse_exercises_exercise_instances',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.exercise_instances_mv TO raw.exercise_instances AS
SELECT * FROM raw.exercise_instances_kafka;
