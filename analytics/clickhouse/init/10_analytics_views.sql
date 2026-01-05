-- ClickHouse: Аналитические витрины

-- dim_users: Справочник пользователей
CREATE TABLE IF NOT EXISTS analytics.dim_users
(
    user_id                   String,
    display_name              Nullable(String),
    sex                       Nullable(String),
    age                       Nullable(Int32),
    bodyweight_kg             Nullable(Float64),
    height_cm                 Nullable(Float64),
    training_experience_level Nullable(String),
    training_experience_years Nullable(Float64),
    primary_default_goal      Nullable(String),
    training_environment      Nullable(String),
    is_public                 Nullable(UInt8),
    is_coach                  Nullable(UInt8),
    coach_accepting_clients   Nullable(UInt8),
    unit_system               Nullable(String),
    timezone                  Nullable(String),
    locale                    Nullable(String),
    created_at                Nullable(DateTime64(3)),
    last_active_at            Nullable(DateTime64(3)),
    _version                  UInt64
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY user_id;

-- dim_exercises: Справочник упражнений
CREATE TABLE IF NOT EXISTS analytics.dim_exercises
(
    exercise_id       Int32,
    name              String,
    muscle_group      Nullable(String),
    equipment         Nullable(String),
    movement_type     Nullable(String),
    region            Nullable(String),
    root_exercise_id  Nullable(Int32),
    target_muscles    Nullable(String),
    synergist_muscles Nullable(String),
    _version          UInt64
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY exercise_id;

-- dim_plans: Справочник планов
CREATE TABLE IF NOT EXISTS analytics.dim_plans
(
    plan_id                     Int32,
    user_id                     String,
    name                        Nullable(String),
    primary_goal                Nullable(String),
    intended_experience_level   Nullable(String),
    intended_frequency_per_week Nullable(Int32),
    duration_weeks              Nullable(Int32),
    is_public                   Nullable(UInt8),
    root_plan_id                Nullable(Int32),
    mesocycles_count            Nullable(Int32),
    _version                    UInt64
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY plan_id;

-- fact_workout_sets: Факт подходов с контекстом
CREATE TABLE IF NOT EXISTS analytics.fact_workout_sets
(
    -- Ключи
    workout_set_id      Int32,
    workout_exercise_id Int32,
    workout_id          Int32,
    user_id             String,
    
    -- Время
    workout_date        Date,
    started_at          Nullable(DateTime64(3)),
    completed_at        Nullable(DateTime64(3)),
    
    -- Упражнение
    exercise_id         Int32,
    
    -- Метрики сета
    intensity           Nullable(Float64),
    effort              Nullable(Float64),
    volume              Nullable(Int32),
    working_weight      Nullable(Float64),
    set_type            Nullable(String),
    
    -- Контекст тренировки
    workout_name        Nullable(String),
    workout_status      Nullable(String),
    rpe_session         Nullable(Float64),
    readiness_score     Nullable(Int32),
    duration_seconds    Nullable(Int32),
    
    -- План (если есть)
    applied_plan_id     Nullable(Int32),
    calendar_plan_id    Nullable(Int32),
    plan_name           Nullable(String),
    
    _version            UInt64
)
ENGINE = ReplacingMergeTree(_version)
PARTITION BY toYYYYMM(workout_date)
ORDER BY (user_id, workout_date, workout_id, workout_set_id);

-- fact_workout_progress: План/Факт сравнение
CREATE TABLE IF NOT EXISTS analytics.fact_workout_progress
(
    -- Ключи
    progress_id        Int32,
    plan_exercise_id   Int32,
    workout_set_id     Int32,
    user_id            String,
    
    -- Время
    date               Date,
    created_at         Nullable(DateTime64(3)),
    
    -- План vs Факт
    planned_intensity  Nullable(Int32),
    actual_intensity   Nullable(Float64),
    intensity_delta    Nullable(Float64),
    
    planned_effort     Nullable(Int32),
    actual_effort      Nullable(Float64),
    effort_delta       Nullable(Float64),
    
    planned_volume     Nullable(Int32),
    actual_volume      Nullable(Int32),
    volume_delta       Nullable(Int32),
    
    -- Контекст
    exercise_id        Nullable(Int32),
    exercise_name      Nullable(String),
    workout_id         Nullable(Int32),
    applied_plan_id    Nullable(Int32),
    
    _version           UInt64
)
ENGINE = ReplacingMergeTree(_version)
PARTITION BY toYYYYMM(date)
ORDER BY (user_id, date, progress_id);

-- fact_user_maxes: Прогрессия силы
CREATE TABLE IF NOT EXISTS analytics.fact_user_maxes
(
    user_max_id     Int32,
    user_id         String,
    exercise_id     Int32,
    exercise_name   Nullable(String),
    date            Date,
    max_weight      Nullable(Int32),
    rep_max         Nullable(Int32),
    true_1rm        Nullable(Float64),
    verified_1rm    Nullable(Float64),
    source          Nullable(String),
    _version        UInt64
)
ENGINE = ReplacingMergeTree(_version)
PARTITION BY toYYYYMM(date)
ORDER BY (user_id, exercise_id, date, user_max_id);

-- fact_plan_adoptions: Подписки на планы
CREATE TABLE IF NOT EXISTS analytics.fact_plan_adoptions
(
    applied_plan_id           Int32,
    user_id                   String,
    calendar_plan_id          Int32,
    plan_name                 Nullable(String),
    plan_author_id            Nullable(String),
    status                    Nullable(String),
    start_date                Nullable(Date),
    end_date                  Nullable(Date),
    planned_sessions_total    Nullable(Int32),
    actual_sessions_completed Nullable(Int32),
    adherence_pct             Nullable(Float64),
    dropped_at                Nullable(DateTime64(3)),
    dropout_reason            Nullable(String),
    _version                  UInt64
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY (user_id, applied_plan_id);

-- fact_coach_payments: Платежи тренерам
CREATE TABLE IF NOT EXISTS analytics.fact_coach_payments
(
    payment_id     Int32,
    link_id        Int32,
    coach_id       String,
    athlete_id     String,
    amount_minor   Nullable(Int32),
    currency       Nullable(String),
    status         Nullable(String),
    valid_until    Nullable(DateTime64(3)),
    created_at     Nullable(DateTime64(3)),
    _version       UInt64
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY (coach_id, ifNull(created_at, toDateTime64(0, 3)), payment_id);
