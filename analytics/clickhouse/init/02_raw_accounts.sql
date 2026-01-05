-- ClickHouse: Raw таблицы для accounts

-- user_profiles
CREATE TABLE IF NOT EXISTS raw.user_profiles
(
    user_id                   String,
    display_name              Nullable(String),
    bio                       Nullable(String),
    photo_url                 Nullable(String),
    bodyweight_kg             Nullable(Float64),
    height_cm                 Nullable(Float64),
    age                       Nullable(Int32),
    sex                       Nullable(String),
    training_experience_years Nullable(Float64),
    training_experience_level Nullable(String),
    primary_default_goal      Nullable(String),
    training_environment      Nullable(String),
    weekly_gain_coef          Nullable(Float64),
    is_public                 Nullable(UInt8),
    last_active_at            Nullable(DateTime64(3)),
    created_at                Nullable(DateTime64(3)),
    updated_at                Nullable(DateTime64(3)),
    __op                      LowCardinality(String),
    __source_ts_ms            Int64,
    _version                  UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY user_id;

CREATE TABLE IF NOT EXISTS raw.user_profiles_kafka
(
    user_id                   String,
    display_name              Nullable(String),
    bio                       Nullable(String),
    photo_url                 Nullable(String),
    bodyweight_kg             Nullable(Float64),
    height_cm                 Nullable(Float64),
    age                       Nullable(Int32),
    sex                       Nullable(String),
    training_experience_years Nullable(Float64),
    training_experience_level Nullable(String),
    primary_default_goal      Nullable(String),
    training_environment      Nullable(String),
    weekly_gain_coef          Nullable(Float64),
    is_public                 Nullable(UInt8),
    last_active_at            Nullable(DateTime64(3)),
    created_at                Nullable(DateTime64(3)),
    updated_at                Nullable(DateTime64(3)),
    __op                      LowCardinality(String),
    __source_ts_ms            Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'accounts-db.public.user_profiles',
    kafka_group_name = 'clickhouse_accounts_user_profiles',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.user_profiles_mv TO raw.user_profiles AS
SELECT * FROM raw.user_profiles_kafka;

-- user_coaching_profiles
CREATE TABLE IF NOT EXISTS raw.user_coaching_profiles
(
    user_id                   String,
    enabled                   Nullable(UInt8),
    accepting_clients         Nullable(UInt8),
    tagline                   Nullable(String),
    description               Nullable(String),
    timezone                  Nullable(String),
    experience_years          Nullable(Int32),
    specializations           Nullable(String),
    languages                 Nullable(String),
    rate_type                 Nullable(String),
    rate_amount_minor         Nullable(Int32),
    rate_currency             Nullable(String),
    stripe_connect_account_id Nullable(String),
    created_at                Nullable(DateTime64(3)),
    updated_at                Nullable(DateTime64(3)),
    __op                      LowCardinality(String),
    __source_ts_ms            Int64,
    _version                  UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY user_id;

CREATE TABLE IF NOT EXISTS raw.user_coaching_profiles_kafka
(
    user_id                   String,
    enabled                   Nullable(UInt8),
    accepting_clients         Nullable(UInt8),
    tagline                   Nullable(String),
    description               Nullable(String),
    timezone                  Nullable(String),
    experience_years          Nullable(Int32),
    specializations           Nullable(String),
    languages                 Nullable(String),
    rate_type                 Nullable(String),
    rate_amount_minor         Nullable(Int32),
    rate_currency             Nullable(String),
    stripe_connect_account_id Nullable(String),
    created_at                Nullable(DateTime64(3)),
    updated_at                Nullable(DateTime64(3)),
    __op                      LowCardinality(String),
    __source_ts_ms            Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'accounts-db.public.user_coaching_profiles',
    kafka_group_name = 'clickhouse_accounts_user_coaching_profiles',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.user_coaching_profiles_mv TO raw.user_coaching_profiles AS
SELECT * FROM raw.user_coaching_profiles_kafka;

-- user_settings
CREATE TABLE IF NOT EXISTS raw.user_settings
(
    user_id               String,
    unit_system           Nullable(String),
    timezone              Nullable(String),
    locale                Nullable(String),
    notifications_enabled Nullable(UInt8),
    created_at            Nullable(DateTime64(3)),
    updated_at            Nullable(DateTime64(3)),
    __op                  LowCardinality(String),
    __source_ts_ms        Int64,
    _version              UInt64 MATERIALIZED __source_ts_ms
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY user_id;

CREATE TABLE IF NOT EXISTS raw.user_settings_kafka
(
    user_id               String,
    unit_system           Nullable(String),
    timezone              Nullable(String),
    locale                Nullable(String),
    notifications_enabled Nullable(UInt8),
    created_at            Nullable(DateTime64(3)),
    updated_at            Nullable(DateTime64(3)),
    __op                  LowCardinality(String),
    __source_ts_ms        Int64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'accounts-db.public.user_settings',
    kafka_group_name = 'clickhouse_accounts_user_settings',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS raw.user_settings_mv TO raw.user_settings AS
SELECT * FROM raw.user_settings_kafka;
