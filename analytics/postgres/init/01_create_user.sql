-- Создание пользователя для Debezium CDC
-- Выполнить на КАЖДОЙ базе данных

-- 1. Создать пользователя с правами репликации
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'debezium') THEN
    CREATE ROLE debezium WITH REPLICATION LOGIN PASSWORD 'DEBEZIUM_PASSWORD_PLACEHOLDER';
  ELSE
    ALTER ROLE debezium WITH REPLICATION LOGIN PASSWORD 'DEBEZIUM_PASSWORD_PLACEHOLDER';
  END IF;
END
$$;

-- 2. Дать права на схему
GRANT USAGE ON SCHEMA public TO debezium;

-- 3. Дать права на чтение всех таблиц
GRANT SELECT ON ALL TABLES IN SCHEMA public TO debezium;

-- 4. Дать права на будущие таблицы
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO debezium;
