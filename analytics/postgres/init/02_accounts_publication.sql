-- База: accounts
-- Выполнить на accounts database

-- Проверить, что wal_level = logical
-- SHOW wal_level;

-- Создать publication для CDC
CREATE PUBLICATION debezium_accounts FOR TABLE
  user_profiles,
  user_coaching_profiles,
  user_settings;
-- user_avatars исключен (bytea blob)

-- Проверить
-- SELECT * FROM pg_publication_tables WHERE pubname = 'debezium_accounts';
