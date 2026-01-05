-- База: exercises
-- Выполнить на exercises database

CREATE PUBLICATION debezium_exercises FOR TABLE
  exercise_list,
  exercise_instances;

-- Проверить
-- SELECT * FROM pg_publication_tables WHERE pubname = 'debezium_exercises';
