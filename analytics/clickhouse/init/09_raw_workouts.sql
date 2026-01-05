-- ClickHouse: Raw таблицы для workouts

-- workouts
CREATE TABLE IF NOT EXISTS raw.workouts
(
    id               Int32,
    user_id          String,
    name             Nullable(String),
    status           Nullable(String),
    workout_type     Nullable(String),
    microcycle_id    Nullable(Int32),
    applied_plan_id  Nullable(Int32),
    plan_order_index Nullable(Int32),
    scheduled_for    Nullable(DateTime64(3)),
    started_at       Nullable(DateTime64(3)),
    completed_at     Nullable(DateTime64(3)),
    duration_seconds Nullable(Int32),
    rpe_session      Nullable(Float64),
    readiness_score  Nullable(Int32),
    location         Nullable(String),
    notes            Nullable(String),
    __op             LowCardinality(String),
    __source_ts_ms   Int64,
    _version         UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.workouts_kafka
(
    id               Int32,
    user_id          String,
    name             Nullable(String),
    status           Nullable(String),
    workout_type     Nullable(String),
    microcycle_id    Nullable(Int32),
    applied_plan_id  Nullable(Int32),
    plan_order_index Nullable(Int32),
    scheduled_for    Nullable(DateTime64(3)),
    started_at       Nullable(DateTime64(3)),
    completed_at     Nullable(DateTime64(3)),
    duration_seconds Nullable(Int32),
    rpe_session      Nullable(Float64),
    readiness_score  Nullable(Int32),
    location         Nullable(String),
    notes            Nullable(String),
    __op             LowCardinality(String),
    __source_ts_ms   Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'workouts-db.public.workouts',
    kafka_group_name = 'clickhouse_workouts_workouts',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.workouts_mv TO raw.workouts AS
SELECT * FROM raw.workouts_kafka;

-- workout_sessions
CREATE TABLE IF NOT EXISTS raw.workout_sessions
(
    id               Int32,
    workout_id       Int32,
    user_id          String,
    status           Nullable(String),
    started_at       Nullable(DateTime64(3)),
    finished_at      Nullable(DateTime64(3)),
    duration_seconds Nullable(Int32),
    progress         Nullable(String),
    macro_suggestion Nullable(String),
    __op             LowCardinality(String),
    __source_ts_ms   Int64,
    _version         UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.workout_sessions_kafka
(
    id               Int32,
    workout_id       Int32,
    user_id          String,
    status           Nullable(String),
    started_at       Nullable(DateTime64(3)),
    finished_at      Nullable(DateTime64(3)),
    duration_seconds Nullable(Int32),
    progress         Nullable(String),
    macro_suggestion Nullable(String),
    __op             LowCardinality(String),
    __source_ts_ms   Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'workouts-db.public.workout_sessions',
    kafka_group_name = 'clickhouse_workouts_workout_sessions',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.workout_sessions_mv TO raw.workout_sessions AS
SELECT * FROM raw.workout_sessions_kafka;

-- workout_exercises
CREATE TABLE IF NOT EXISTS raw.workout_exercises
(
    id             Int32,
    workout_id     Int32,
    exercise_id    Int32,
    user_id        String,
    __op           LowCardinality(String),
    __source_ts_ms Int64,
    _version       UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.workout_exercises_kafka
(
    id             Int32,
    workout_id     Int32,
    exercise_id    Int32,
    user_id        String,
    __op           LowCardinality(String),
    __source_ts_ms Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'workouts-db.public.workout_exercises',
    kafka_group_name = 'clickhouse_workouts_workout_exercises',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.workout_exercises_mv TO raw.workout_exercises AS
SELECT * FROM raw.workout_exercises_kafka;

-- workout_sets
CREATE TABLE IF NOT EXISTS raw.workout_sets
(
    id             Int32,
    exercise_id    Int32,
    intensity      Nullable(Float64),
    effort         Nullable(Float64),
    volume         Nullable(Int32),
    working_weight Nullable(Float64),
    set_type       Nullable(String),
    __op           LowCardinality(String),
    __source_ts_ms Int64,
    _version       UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY id;

CREATE TABLE IF NOT EXISTS raw.workout_sets_kafka
(
    id             Int32,
    exercise_id    Int32,
    intensity      Nullable(Float64),
    effort         Nullable(Float64),
    volume         Nullable(Int32),
    working_weight Nullable(Float64),
    set_type       Nullable(String),
    __op           LowCardinality(String),
    __source_ts_ms Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'workouts-db.public.workout_sets',
    kafka_group_name = 'clickhouse_workouts_workout_sets',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.workout_sets_mv TO raw.workout_sets AS
SELECT * FROM raw.workout_sets_kafka;
