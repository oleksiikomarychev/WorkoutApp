-- База: plans
-- Выполнить на plans database

CREATE PUBLICATION debezium_plans FOR TABLE
  calendar_plans,
  mesocycles,
  microcycles,
  plan_workouts,
  plan_exercises,
  plan_sets,
  plan_macros,
  mesocycle_templates,
  microcycle_templates,
  applied_calendar_plans,
  applied_mesocycles,
  applied_microcycles,
  applied_workouts,
  applied_plan_workouts,
  plan_adopters,
  workout_progress;

-- Проверить
-- SELECT * FROM pg_publication_tables WHERE pubname = 'debezium_plans';
