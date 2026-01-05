-- База: agent
-- Выполнить на agent database

CREATE PUBLICATION debezium_agent FOR TABLE
  generated_plans;

-- Проверить
-- SELECT * FROM pg_publication_tables WHERE pubname = 'debezium_agent';
