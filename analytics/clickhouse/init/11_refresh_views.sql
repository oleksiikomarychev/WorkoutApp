-- ClickHouse: SQL для обновления аналитических витрин
-- Выполнять периодически (например, каждый час) или по триггеру

-- Обновить dim_users
INSERT INTO analytics.dim_users
SELECT
    up.user_id,
    up.display_name,
    up.sex,
    up.age,
    up.bodyweight_kg,
    up.height_cm,
    up.training_experience_level,
    up.training_experience_years,
    up.primary_default_goal,
    up.training_environment,
    up.is_public,
    if(ucp.user_id != '', 1, 0) AS is_coach,
    ucp.accepting_clients AS coach_accepting_clients,
    us.unit_system,
    us.timezone,
    us.locale,
    up.created_at,
    up.last_active_at,
    toUInt64(now64(3)) AS _version
FROM raw.user_profiles up FINAL
LEFT JOIN raw.user_coaching_profiles ucp FINAL ON up.user_id = ucp.user_id
LEFT JOIN raw.user_settings us FINAL ON up.user_id = us.user_id
WHERE up.__op != 'd';

-- Обновить dim_exercises
INSERT INTO analytics.dim_exercises
SELECT
    id AS exercise_id,
    name,
    muscle_group,
    equipment,
    movement_type,
    region,
    root_exercise_id,
    target_muscles,
    synergist_muscles,
    toUInt64(now64(3)) AS _version
FROM raw.exercise_list FINAL
WHERE __op != 'd';

-- Обновить dim_plans
INSERT INTO analytics.dim_plans
SELECT
    cp.id AS plan_id,
    cp.user_id,
    cp.name,
    cp.primary_goal,
    cp.intended_experience_level,
    cp.intended_frequency_per_week,
    cp.duration_weeks,
    cp.is_public,
    cp.root_plan_id,
    count(DISTINCT m.id) AS mesocycles_count,
    toUInt64(now64(3)) AS _version
FROM raw.calendar_plans cp FINAL
LEFT JOIN raw.mesocycles m FINAL ON cp.id = m.calendar_plan_id
WHERE cp.__op != 'd'
GROUP BY
    cp.id, cp.user_id, cp.name, cp.primary_goal,
    cp.intended_experience_level, cp.intended_frequency_per_week,
    cp.duration_weeks, cp.is_public, cp.root_plan_id;

-- Обновить fact_workout_sets
INSERT INTO analytics.fact_workout_sets
SELECT
    ws.id AS workout_set_id,
    ws.exercise_id AS workout_exercise_id,
    we.workout_id,
    w.user_id,
    
    toDate(coalesce(w.started_at, w.scheduled_for, now())) AS workout_date,
    w.started_at,
    w.completed_at,
    
    we.exercise_id,
    
    ws.intensity,
    ws.effort,
    ws.volume,
    ws.working_weight,
    ws.set_type,
    
    w.name AS workout_name,
    w.status AS workout_status,
    w.rpe_session,
    w.readiness_score,
    w.duration_seconds,
    
    w.applied_plan_id,
    acp.calendar_plan_id,
    cp.name AS plan_name,
    
    toUInt64(now64(3)) AS _version
FROM raw.workout_sets ws FINAL
JOIN raw.workout_exercises we FINAL ON ws.exercise_id = we.id
JOIN raw.workouts w FINAL ON we.workout_id = w.id
LEFT JOIN raw.applied_calendar_plans acp FINAL ON w.applied_plan_id = acp.id
LEFT JOIN raw.calendar_plans cp FINAL ON acp.calendar_plan_id = cp.id
WHERE ws.__op != 'd';

 -- Обновить fact_workout_progress
 INSERT INTO analytics.fact_workout_progress
 SELECT
     wp.id AS progress_id,
     wp.plan_exercise_id,
     wp.workout_set_id,
     w.user_id,
 
     toDate(coalesce(wp.date, wp.created_at, now())) AS date,
     wp.created_at,
 
     wp.planned_intensity,
     wp.actual_intensity,
     ifNull(wp.actual_intensity, 0) - toFloat64(ifNull(wp.planned_intensity, 0)) AS intensity_delta,
 
     wp.planned_effort,
     wp.actual_effort,
     ifNull(wp.actual_effort, 0) - toFloat64(ifNull(wp.planned_effort, 0)) AS effort_delta,
 
     wp.planned_volume,
     wp.actual_volume,
     ifNull(wp.actual_volume, 0) - ifNull(wp.planned_volume, 0) AS volume_delta,
 
     we.exercise_id AS exercise_id,
     el.name AS exercise_name,
     w.id AS workout_id,
     w.applied_plan_id AS applied_plan_id,
 
     toUInt64(now64(3)) AS _version
 FROM raw.workout_progress wp FINAL
 JOIN raw.workout_sets ws FINAL ON wp.workout_set_id = ws.id
 JOIN raw.workout_exercises we FINAL ON ws.exercise_id = we.id
 JOIN raw.workouts w FINAL ON we.workout_id = w.id
 LEFT JOIN raw.exercise_list el FINAL ON we.exercise_id = el.id
 WHERE wp.__op != 'd';

-- Обновить fact_user_maxes
INSERT INTO analytics.fact_user_maxes
SELECT
    id AS user_max_id,
    user_id,
    exercise_id,
    exercise_name,
    coalesce(date, today()) AS date,
    max_weight,
    rep_max,
    true_1rm,
    verified_1rm,
    source,
    toUInt64(now64(3)) AS _version
FROM raw.user_maxes FINAL
WHERE __op != 'd';

-- Обновить fact_plan_adoptions
INSERT INTO analytics.fact_plan_adoptions
SELECT
    acp.id AS applied_plan_id,
    acp.user_id,
    acp.calendar_plan_id,
    cp.name AS plan_name,
    cp.user_id AS plan_author_id,
    acp.status,
    toDate(acp.start_date) AS start_date,
    toDate(acp.end_date) AS end_date,
    acp.planned_sessions_total,
    acp.actual_sessions_completed,
    acp.adherence_pct,
    acp.dropped_at,
    acp.dropout_reason,
    toUInt64(now64(3)) AS _version
FROM raw.applied_calendar_plans acp FINAL
LEFT JOIN raw.calendar_plans cp FINAL ON acp.calendar_plan_id = cp.id
WHERE acp.__op != 'd';

-- Обновить fact_coach_payments
INSERT INTO analytics.fact_coach_payments
SELECT
    id AS payment_id,
    link_id,
    coach_id,
    athlete_id,
    amount_minor,
    currency,
    status,
    valid_until,
    created_at,
    toUInt64(now64(3)) AS _version
FROM raw.coach_athlete_payments FINAL
WHERE __op != 'd';
