# Analytics CDC Pipeline

Postgres → Debezium → Kafka → ClickHouse

## Структура

```
analytics/
├── debezium/
│   └── connectors/          # JSON конфиги для 7 Debezium коннекторов
├── clickhouse/
│   ├── init/                # SQL для инициализации ClickHouse
│   └── config/              # Конфигурация ClickHouse
├── postgres/
│   └── init/                # SQL для настройки logical replication
├── scripts/
│   ├── setup-postgres.sh    # Настройка всех Postgres БД
│   ├── deploy-connectors.sh # Деплой Debezium коннекторов
│   └── init-clickhouse.sh   # Инициализация ClickHouse таблиц
└── README.md
```

## Быстрый старт (локально)

### 1. Запустить CDC инфраструктуру

```bash
# Из корня проекта
docker compose up -d zookeeper kafka schema-registry debezium-connect clickhouse
```

### 2. Настроить Postgres для CDC

```bash
./analytics/scripts/setup-postgres.sh
```

### 3. Задеплоить Debezium коннекторы

```bash
./analytics/scripts/deploy-connectors.sh
```

### 4. Инициализировать ClickHouse таблицы

```bash
./analytics/scripts/init-clickhouse.sh
```

### 5. Проверить статус

```bash
# Проверить коннекторы
curl http://localhost:8083/connectors | jq

# Проверить топики Kafka
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Проверить данные в ClickHouse
docker exec -it clickhouse clickhouse-client -q "SELECT count() FROM raw.workouts"
```

## Production (Hetzner)

```bash
# На сервере
docker compose -f docker-compose.prod.yml up -d zookeeper kafka schema-registry debezium-connect clickhouse

# Настроить Postgres (выполнить на каждой БД)
./analytics/scripts/setup-postgres.sh prod

# Задеплоить коннекторы
./analytics/scripts/deploy-connectors.sh prod

# Инициализировать ClickHouse
./analytics/scripts/init-clickhouse.sh prod
```

## Мониторинг

- **Debezium UI**: http://localhost:8083 (API)
- **ClickHouse**: http://localhost:8123 (HTTP), порт 9000 (native)
- **Kafka**: порт 9092

## Переменные окружения

Добавить в `.env`:

```bash
# ClickHouse
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=clickhouse_password_here

# Debezium
DEBEZIUM_USER=debezium
DEBEZIUM_PASSWORD=debezium_password_here
```

## Таблицы

### Raw-слой (реплика Postgres)
- `raw.user_profiles`, `raw.user_coaching_profiles`, `raw.user_settings`
- `raw.generated_plans`
- `raw.coach_athlete_*` (6 таблиц)
- `raw.exercise_list`, `raw.exercise_instances`
- `raw.user_maxes`, `raw.user_max_daily_agg`
- `raw.calendar_plans`, `raw.mesocycles`, `raw.microcycles`, ... (16 таблиц)
- `raw.workouts`, `raw.workout_sessions`, `raw.workout_exercises`, `raw.workout_sets`

### Аналитический слой (витрины)
- `analytics.fact_workout_sets` — подходы с контекстом
- `analytics.fact_workout_progress` — план/факт
- `analytics.fact_user_maxes` — прогрессия силы
- `analytics.dim_users` — пользователи
- `analytics.dim_exercises` — упражнения
- `analytics.dim_plans` — планы

## Данные для персонализации RPE

Приложение пока не собирает подтверждённый пользователем RPE отдельно от автоматически рассчитанного. В текущих витринах `fact_workout_sets.effort` и `fact_workout_progress.actual_effort` нет происхождения значения; эти поля нельзя считать обучающими метками. Выполнение подхода хранится в `workout_sessions.progress.completed`, а `workout_sets` содержит изменяемые параметры подхода.

План: добавить в `workouts-service` отдельное наблюдение на пару `(workout_session_id, workout_set_id)` со снимком фактических веса и повторов, их происхождением, `predicted_rpe`, необязательным `actual_rpe`, `actual_rpe_source`, `feedback_method`, временем подтверждения, версией прогноза и транзакционной `revision`. После миграции PostgreSQL обновить publication, `workouts-connector.json`, raw-таблицу и новую витрину `fact_rpe_observations`; проверить вставку, правку, отмену, повтор CDC-события и удаление. Для воспроизводимой калибровки сохранять неизменяемый snapshot фактических признаков и версий, а не полагаться на текущее состояние ClickHouse. Старые витрины не следует объявлять датасетом задним числом. Подробности — в [плане RPE Engine](../services/rpe-service/autonomy_plan.md).
