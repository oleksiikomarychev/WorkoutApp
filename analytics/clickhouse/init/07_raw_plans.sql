-- ClickHouse: Raw таблицы для plans (часть 1 - основные)

-- calendar_plans
CREATE TABLE IF NOT EXISTS raw.calendar_plans
(
    id                           Int32,
    user_id                      String,
    name                         Nullable(String),
    notes                        Nullable(String),
    primary_goal                 Nullable(String),
    intended_experience_level    Nullable(String),
    intended_frequency_per_week  Nullable(Int32),
    session_duration_target_min  Nullable(Int32),
    duration_weeks               Nullable(Int32),
    primary_focus_lifts          Nullable(String),
    required_equipment           Nullable(String),
    is_public                    Nullable(UInt8),
    is_active                    Nullable(UInt8),
    root_plan_id                 Nullable(Int32),
    __op                         LowCardinality(String),
    __source_ts_ms               Int64,
    _version                     UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.calendar_plans_kafka
(
    id                           Int32,
    user_id                      String,
    name                         Nullable(String),
    notes                        Nullable(String),
    primary_goal                 Nullable(String),
    intended_experience_level    Nullable(String),
    intended_frequency_per_week  Nullable(Int32),
    session_duration_target_min  Nullable(Int32),
    duration_weeks               Nullable(Int32),
    primary_focus_lifts          Nullable(String),
    required_equipment           Nullable(String),
    is_public                    Nullable(UInt8),
    is_active                    Nullable(UInt8),
    root_plan_id                 Nullable(Int32),
    __op                         LowCardinality(String),
    __source_ts_ms               Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'plans-db.public.calendar_plans',
    kafka_group_name = 'clickhouse_plans_calendar_plans',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.calendar_plans_mv TO raw.calendar_plans AS
SELECT * FROM raw.calendar_plans_kafka;

-- mesocycles
CREATE TABLE IF NOT EXISTS raw.mesocycles
(
    id                    Int32,
    calendar_plan_id      Int32,
    name                  Nullable(String),
    notes                 Nullable(String),
    order_index           Nullable(Int32),
    duration_weeks        Nullable(Int32),
    weeks_count           Nullable(Int32),
    microcycle_length_days Nullable(Int32),
    __op                  LowCardinality(String),
    __source_ts_ms        Int64,
    _version              UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.mesocycles_kafka
(
    id                    Int32,
    calendar_plan_id      Int32,
    name                  Nullable(String),
    notes                 Nullable(String),
    order_index           Nullable(Int32),
    duration_weeks        Nullable(Int32),
    weeks_count           Nullable(Int32),
    microcycle_length_days Nullable(Int32),
    __op                  LowCardinality(String),
    __source_ts_ms        Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'plans-db.public.mesocycles',
    kafka_group_name = 'clickhouse_plans_mesocycles',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.mesocycles_mv TO raw.mesocycles AS
SELECT * FROM raw.mesocycles_kafka;

-- microcycles
CREATE TABLE IF NOT EXISTS raw.microcycles
(
    id                  Int32,
    mesocycle_id        Int32,
    name                Nullable(String),
    notes               Nullable(String),
    order_index         Nullable(Int32),
    days_count          Nullable(Int32),
    normalization_value Nullable(Float64),
    normalization_unit  Nullable(String),
    normalization_rules Nullable(String),
    __op                LowCardinality(String),
    __source_ts_ms      Int64,
    _version            UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.microcycles_kafka
(
    id                  Int32,
    mesocycle_id        Int32,
    name                Nullable(String),
    notes               Nullable(String),
    order_index         Nullable(Int32),
    days_count          Nullable(Int32),
    normalization_value Nullable(Float64),
    normalization_unit  Nullable(String),
    normalization_rules Nullable(String),
    __op                LowCardinality(String),
    __source_ts_ms      Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'plans-db.public.microcycles',
    kafka_group_name = 'clickhouse_plans_microcycles',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.microcycles_mv TO raw.microcycles AS
SELECT * FROM raw.microcycles_kafka;

-- plan_workouts
CREATE TABLE IF NOT EXISTS raw.plan_workouts
(
    id             Int32,
    microcycle_id  Int32,
    order_index    Nullable(Int32),
    day_label      Nullable(String),
    created_at     Nullable(DateTime64(3)),
    updated_at     Nullable(DateTime64(3)),
    __op           LowCardinality(String),
    __source_ts_ms Int64,
    _version       UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.plan_workouts_kafka
(
    id             Int32,
    microcycle_id  Int32,
    order_index    Nullable(Int32),
    day_label      Nullable(String),
    created_at     Nullable(DateTime64(3)),
    updated_at     Nullable(DateTime64(3)),
    __op           LowCardinality(String),
    __source_ts_ms Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'plans-db.public.plan_workouts',
    kafka_group_name = 'clickhouse_plans_plan_workouts',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.plan_workouts_mv TO raw.plan_workouts AS
SELECT * FROM raw.plan_workouts_kafka;

-- plan_exercises
CREATE TABLE IF NOT EXISTS raw.plan_exercises
(
    id                     Int32,
    plan_workout_id        Int32,
    exercise_definition_id Nullable(Int32),
    exercise_name          Nullable(String),
    order_index            Nullable(Int32),
    created_at             Nullable(DateTime64(3)),
    updated_at             Nullable(DateTime64(3)),
    __op                   LowCardinality(String),
    __source_ts_ms         Int64,
    _version               UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.plan_exercises_kafka
(
    id                     Int32,
    plan_workout_id        Int32,
    exercise_definition_id Nullable(Int32),
    exercise_name          Nullable(String),
    order_index            Nullable(Int32),
    created_at             Nullable(DateTime64(3)),
    updated_at             Nullable(DateTime64(3)),
    __op                   LowCardinality(String),
    __source_ts_ms         Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'plans-db.public.plan_exercises',
    kafka_group_name = 'clickhouse_plans_plan_exercises',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.plan_exercises_mv TO raw.plan_exercises AS
SELECT * FROM raw.plan_exercises_kafka;

-- plan_sets
CREATE TABLE IF NOT EXISTS raw.plan_sets
(
    id               Int32,
    plan_exercise_id Int32,
    order_index      Nullable(Int32),
    intensity        Nullable(Int32),
    effort           Nullable(Int32),
    volume           Nullable(Int32),
    working_weight   Nullable(Float64),
    created_at       Nullable(DateTime64(3)),
    updated_at       Nullable(DateTime64(3)),
    __op             LowCardinality(String),
    __source_ts_ms   Int64,
    _version         UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.plan_sets_kafka
(
    id               Int32,
    plan_exercise_id Int32,
    order_index      Nullable(Int32),
    intensity        Nullable(Int32),
    effort           Nullable(Int32),
    volume           Nullable(Int32),
    working_weight   Nullable(Float64),
    created_at       Nullable(DateTime64(3)),
    updated_at       Nullable(DateTime64(3)),
    __op             LowCardinality(String),
    __source_ts_ms   Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'plans-db.public.plan_sets',
    kafka_group_name = 'clickhouse_plans_plan_sets',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.plan_sets_mv TO raw.plan_sets AS
SELECT * FROM raw.plan_sets_kafka;

-- plan_macros
CREATE TABLE IF NOT EXISTS raw.plan_macros
(
    id               Int32,
    calendar_plan_id Int32,
    name             Nullable(String),
    rule_json        Nullable(String),
    priority         Nullable(Int32),
    is_active        Nullable(UInt8),
    created_at       Nullable(DateTime64(3)),
    updated_at       Nullable(DateTime64(3)),
    __op             LowCardinality(String),
    __source_ts_ms   Int64,
    _version         UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.plan_macros_kafka
(
    id               Int32,
    calendar_plan_id Int32,
    name             Nullable(String),
    rule_json        Nullable(String),
    priority         Nullable(Int32),
    is_active        Nullable(UInt8),
    created_at       Nullable(DateTime64(3)),
    updated_at       Nullable(DateTime64(3)),
    __op             LowCardinality(String),
    __source_ts_ms   Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'plans-db.public.plan_macros',
    kafka_group_name = 'clickhouse_plans_plan_macros',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.plan_macros_mv TO raw.plan_macros AS
SELECT * FROM raw.plan_macros_kafka;
