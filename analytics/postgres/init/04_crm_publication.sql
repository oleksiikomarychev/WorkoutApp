-- База: crm
-- Выполнить на crm database

CREATE PUBLICATION debezium_crm FOR TABLE
  coach_athlete_links,
  coach_athlete_events,
  coach_athlete_notes,
  coach_athlete_tags,
  coach_athlete_link_tags,
  coach_athlete_payments;

-- Проверить
-- SELECT * FROM pg_publication_tables WHERE pubname = 'debezium_crm';
