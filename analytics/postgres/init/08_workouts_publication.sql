-- База: workouts
-- Выполнить на workouts database

CREATE PUBLICATION debezium_workouts FOR TABLE
  workouts,
  workout_sessions,
  workout_exercises,
  workout_sets;

-- Проверить
-- SELECT * FROM pg_publication_tables WHERE pubname = 'debezium_workouts';
