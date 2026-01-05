-- ClickHouse: Raw таблицы для plans (часть 2 - applied таблицы)

-- applied_calendar_plans
CREATE TABLE IF NOT EXISTS raw.applied_calendar_plans
(
    id                        Int32,
    user_id                   String,
    calendar_plan_id          Int32,
    status                    Nullable(String),
    start_date                Nullable(DateTime64(3)),
    end_date                  Nullable(DateTime64(3)),
    is_active                 Nullable(UInt8),
    current_workout_index     Nullable(Int32),
    planned_sessions_total    Nullable(Int32),
    actual_sessions_completed Nullable(Int32),
    adherence_pct             Nullable(Float64),
    dropped_at                Nullable(DateTime64(3)),
    dropout_reason            Nullable(String),
    notes                     Nullable(String),
    user_max_ids              Nullable(String),
    __op                      LowCardinality(String),
    __source_ts_ms            Int64,
    _version                  UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.applied_calendar_plans_kafka
(
    id                        Int32,
    user_id                   String,
    calendar_plan_id          Int32,
    status                    Nullable(String),
    start_date                Nullable(DateTime64(3)),
    end_date                  Nullable(DateTime64(3)),
    is_active                 Nullable(UInt8),
    current_workout_index     Nullable(Int32),
    planned_sessions_total    Nullable(Int32),
    actual_sessions_completed Nullable(Int32),
    adherence_pct             Nullable(Float64),
    dropped_at                Nullable(DateTime64(3)),
    dropout_reason            Nullable(String),
    notes                     Nullable(String),
    user_max_ids              Nullable(String),
    __op                      LowCardinality(String),
    __source_ts_ms            Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'plans-db.public.applied_calendar_plans',
    kafka_group_name = 'clickhouse_plans_applied_calendar_plans',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.applied_calendar_plans_mv TO raw.applied_calendar_plans AS
SELECT * FROM raw.applied_calendar_plans_kafka;

-- applied_mesocycles
CREATE TABLE IF NOT EXISTS raw.applied_mesocycles
(
    id              Int32,
    applied_plan_id Int32,
    mesocycle_id    Int32,
    order_index     Nullable(Int32),
    __op            LowCardinality(String),
    __source_ts_ms  Int64,
    _version        UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.applied_mesocycles_kafka
(
    id              Int32,
    applied_plan_id Int32,
    mesocycle_id    Int32,
    order_index     Nullable(Int32),
    __op            LowCardinality(String),
    __source_ts_ms  Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'plans-db.public.applied_mesocycles',
    kafka_group_name = 'clickhouse_plans_applied_mesocycles',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.applied_mesocycles_mv TO raw.applied_mesocycles AS
SELECT * FROM raw.applied_mesocycles_kafka;

-- applied_microcycles
CREATE TABLE IF NOT EXISTS raw.applied_microcycles
(
    id                   Int32,
    applied_mesocycle_id Int32,
    microcycle_id        Int32,
    order_index          Nullable(Int32),
    __op                 LowCardinality(String),
    __source_ts_ms       Int64,
    _version             UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.applied_microcycles_kafka
(
    id                   Int32,
    applied_mesocycle_id Int32,
    microcycle_id        Int32,
    order_index          Nullable(Int32),
    __op                 LowCardinality(String),
    __source_ts_ms       Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'plans-db.public.applied_microcycles',
    kafka_group_name = 'clickhouse_plans_applied_microcycles',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.applied_microcycles_mv TO raw.applied_microcycles AS
SELECT * FROM raw.applied_microcycles_kafka;

-- applied_workouts
CREATE TABLE IF NOT EXISTS raw.applied_workouts
(
    id                    Int32,
    applied_microcycle_id Int32,
    workout_id            Int32,
    order_index           Nullable(Int32),
    __op                  LowCardinality(String),
    __source_ts_ms        Int64,
    _version              UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.applied_workouts_kafka
(
    id                    Int32,
    applied_microcycle_id Int32,
    workout_id            Int32,
    order_index           Nullable(Int32),
    __op                  LowCardinality(String),
    __source_ts_ms        Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'plans-db.public.applied_workouts',
    kafka_group_name = 'clickhouse_plans_applied_workouts',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.applied_workouts_mv TO raw.applied_workouts AS
SELECT * FROM raw.applied_workouts_kafka;

-- applied_plan_workouts
CREATE TABLE IF NOT EXISTS raw.applied_plan_workouts
(
    id              Int32,
    applied_plan_id Int32,
    workout_id      Int32,
    order_index     Nullable(Int32),
    __op            LowCardinality(String),
    __source_ts_ms  Int64,
    _version        UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.applied_plan_workouts_kafka
(
    id              Int32,
    applied_plan_id Int32,
    workout_id      Int32,
    order_index     Nullable(Int32),
    __op            LowCardinality(String),
    __source_ts_ms  Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'plans-db.public.applied_plan_workouts',
    kafka_group_name = 'clickhouse_plans_applied_plan_workouts',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.applied_plan_workouts_mv TO raw.applied_plan_workouts AS
SELECT * FROM raw.applied_plan_workouts_kafka;

-- plan_adopters
CREATE TABLE IF NOT EXISTS raw.plan_adopters
(
    root_plan_id     Int32,
    adopter_user_id  String,
    first_applied_at Nullable(DateTime64(3)),
    created_at       Nullable(DateTime64(3)),
    __op             LowCardinality(String),
    __source_ts_ms   Int64,
    _version         UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY (root_plan_id, adopter_user_id);

CREATE TABLE IF NOT EXISTS raw.plan_adopters_kafka
(
    root_plan_id     Int32,
    adopter_user_id  String,
    first_applied_at Nullable(DateTime64(3)),
    created_at       Nullable(DateTime64(3)),
    __op             LowCardinality(String),
    __source_ts_ms   Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'plans-db.public.plan_adopters',
    kafka_group_name = 'clickhouse_plans_plan_adopters',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.plan_adopters_mv TO raw.plan_adopters AS
SELECT * FROM raw.plan_adopters_kafka;

-- workout_progress
CREATE TABLE IF NOT EXISTS raw.workout_progress
(
    id               Int32,
    plan_exercise_id Int32,
    workout_set_id   Int32,
    planned_intensity Nullable(Int32),
    actual_intensity  Nullable(Float64),
    planned_effort    Nullable(Int32),
    actual_effort     Nullable(Float64),
    planned_volume    Nullable(Int32),
    actual_volume     Nullable(Int32),
    date              Nullable(DateTime64(3)),
    created_at        Nullable(DateTime64(3)),
    __op              LowCardinality(String),
    __source_ts_ms    Int64,
    _version          UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.workout_progress_kafka
(
    id               Int32,
    plan_exercise_id Int32,
    workout_set_id   Int32,
    planned_intensity Nullable(Int32),
    actual_intensity  Nullable(Float64),
    planned_effort    Nullable(Int32),
    actual_effort     Nullable(Float64),
    planned_volume    Nullable(Int32),
    actual_volume     Nullable(Int32),
    date              Nullable(DateTime64(3)),
    created_at        Nullable(DateTime64(3)),
    __op              LowCardinality(String),
    __source_ts_ms    Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'plans-db.public.workout_progress',
    kafka_group_name = 'clickhouse_plans_workout_progress',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.workout_progress_mv TO raw.workout_progress AS
SELECT * FROM raw.workout_progress_kafka;

-- mesocycle_templates
CREATE TABLE IF NOT EXISTS raw.mesocycle_templates
(
    id                     Int32,
    user_id                String,
    name                   Nullable(String),
    notes                  Nullable(String),
    weeks_count            Nullable(Int32),
    microcycle_length_days Nullable(Int32),
    normalization_value    Nullable(Int32),
    normalization_unit     Nullable(String),
    is_public              Nullable(UInt8),
    created_at             Nullable(DateTime64(3)),
    updated_at             Nullable(DateTime64(3)),
    __op                   LowCardinality(String),
    __source_ts_ms         Int64,
    _version               UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.mesocycle_templates_kafka
(
    id                     Int32,
    user_id                String,
    name                   Nullable(String),
    notes                  Nullable(String),
    weeks_count            Nullable(Int32),
    microcycle_length_days Nullable(Int32),
    normalization_value    Nullable(Int32),
    normalization_unit     Nullable(String),
    is_public              Nullable(UInt8),
    created_at             Nullable(DateTime64(3)),
    updated_at             Nullable(DateTime64(3)),
    __op                   LowCardinality(String),
    __source_ts_ms         Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'plans-db.public.mesocycle_templates',
    kafka_group_name = 'clickhouse_plans_mesocycle_templates',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.mesocycle_templates_mv TO raw.mesocycle_templates AS
SELECT * FROM raw.mesocycle_templates_kafka;

-- microcycle_templates
CREATE TABLE IF NOT EXISTS raw.microcycle_templates
(
    id                    Int32,
    mesocycle_template_id Int32,
    name                  Nullable(String),
    notes                 Nullable(String),
    order_index           Nullable(Int32),
    days_count            Nullable(Int32),
    schedule_json         Nullable(String),
    __op                  LowCardinality(String),
    __source_ts_ms        Int64,
    _version              UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.microcycle_templates_kafka
(
    id                    Int32,
    mesocycle_template_id Int32,
    name                  Nullable(String),
    notes                 Nullable(String),
    order_index           Nullable(Int32),
    days_count            Nullable(Int32),
    schedule_json         Nullable(String),
    __op                  LowCardinality(String),
    __source_ts_ms        Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'plans-db.public.microcycle_templates',
    kafka_group_name = 'clickhouse_plans_microcycle_templates',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.microcycle_templates_mv TO raw.microcycle_templates AS
SELECT * FROM raw.microcycle_templates_kafka;
