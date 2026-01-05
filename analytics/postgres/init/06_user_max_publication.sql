-- База: user_max
-- Выполнить на user_max database

CREATE PUBLICATION debezium_user_max FOR TABLE
  user_maxes,
  user_max_daily_agg;

-- Проверить
-- SELECT * FROM pg_publication_tables WHERE pubname = 'debezium_user_max';
