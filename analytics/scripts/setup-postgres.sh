#!/bin/bash
set -e

# Настройка Postgres баз данных для CDC
# Использование:
#   ./setup-postgres.sh                 # local, .env
#   ./setup-postgres.sh prod            # prod, .env.example
#   ./setup-postgres.sh local .env      # явный env файл
#   ./setup-postgres.sh prod  .env.prod # явный env файл

ENV="${1:-local}"
ENV_FILE="${2:-}"

if [ -z "$ENV_FILE" ]; then
  if [ "$ENV" = "prod" ]; then
    ENV_FILE=".env.example"
  else
    ENV_FILE=".env"
  fi
fi

echo "=== Настройка Postgres для CDC (среда: $ENV, env: $ENV_FILE) ==="

if [ ! -f "$ENV_FILE" ]; then
  echo "ОШИБКА: env файл не найден: $ENV_FILE"
  exit 1
fi

load_env_file() {
  local file="$1"
  while IFS= read -r line || [ -n "$line" ]; do
    # strip leading/trailing whitespace
    line="$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

    # skip empty and comments
    if [ -z "$line" ] || [[ "$line" == \#* ]]; then
      continue
    fi

    # must contain '='
    if [[ "$line" != *"="* ]]; then
      continue
    fi

    local key="${line%%=*}"
    local value="${line#*=}"

    key="$(echo "$key" | sed -e 's/[[:space:]]//g')"
    value="$(echo "$value" | sed -e 's/^[[:space:]]*//')"

    # validate key name
    if [[ ! "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      continue
    fi

    export "$key=$value"
  done < "$file"
}

load_env_file "$ENV_FILE"

if [ -z "${DEBEZIUM_PASSWORD:-}" ]; then
  echo "ОШИБКА: DEBEZIUM_PASSWORD не задан в $ENV_FILE"
  exit 1
fi

SQL_DIR="$(dirname "$0")/../postgres/init"

PSQL_IMAGE="postgres:16-alpine"

psql_docker() {
  local db_url="$1"

  # normalize schemes: postgresql+asyncpg:// -> postgresql://
  db_url="${db_url/postgresql+asyncpg:\/\//postgresql://}"

  # Remove any stray backslashes (sometimes env parsing introduces them)
  db_url="${db_url//\\/}"

  # If sslmode key is present but has no value (e.g. ?sslmode), default to require.
  if [[ "$db_url" =~ ([\?&]sslmode)$ ]]; then
    db_url="${db_url}=require"
  fi
  docker run --rm -i "$PSQL_IMAGE" psql "$db_url" -v ON_ERROR_STOP=1
}

apply_sql_file() {
  local db_url="$1"
  local sql_file="$2"
  local title="$3"

  echo ">>> $title"
  sed "s/DEBEZIUM_PASSWORD_PLACEHOLDER/${DEBEZIUM_PASSWORD}/g" "$sql_file" | psql_docker "$db_url"
  echo ">>> OK: $title"
}

drop_publication_if_exists() {
  local db_url="$1"
  local pub_name="$2"
  echo "DROP PUBLICATION IF EXISTS ${pub_name};" | psql_docker "$db_url" > /dev/null
}

apply_db() {
  local db_key="$1"
  local db_url="$2"
  local pub_name="$3"
  local pub_sql_file="$4"

  if [ -z "$db_url" ]; then
    return 0
  fi

  echo ""
  echo "=== DB: $db_key ==="
  apply_sql_file "$db_url" "$SQL_DIR/01_create_user.sql" "$db_key: create/update debezium role"

  if [ -n "$pub_name" ] && [ -n "$pub_sql_file" ]; then
    drop_publication_if_exists "$db_url" "$pub_name"
    apply_sql_file "$db_url" "$pub_sql_file" "$db_key: create publication $pub_name"
  fi
}

echo ""
echo "=== Шаг 0: Проверка wal_level ==="
echo "Ты писал что wal_level=logical уже включен. Если нужно проверить:"
echo "  SHOW wal_level;"

apply_db "accounts"  "${ACCOUNTS_DATABASE_URL:-}"  "debezium_accounts"   "$SQL_DIR/02_accounts_publication.sql"
apply_db "agent"     "${AGENT_DATABASE_URL:-}"     "debezium_agent"      "$SQL_DIR/03_agent_publication.sql"
apply_db "crm"       "${CRM_DATABASE_URL:-}"       "debezium_crm"        "$SQL_DIR/04_crm_publication.sql"
apply_db "exercises" "${EXERCISES_DATABASE_URL:-}" "debezium_exercises"  "$SQL_DIR/05_exercises_publication.sql"
apply_db "user_max"  "${USER_MAX_DATABASE_URL:-}"  "debezium_user_max"   "$SQL_DIR/06_user_max_publication.sql"
apply_db "plans"     "${PLANS_DATABASE_URL:-}"     "debezium_plans"      "$SQL_DIR/07_plans_publication.sql"
apply_db "workouts"  "${WORKOUTS_DATABASE_URL:-}"  "debezium_workouts"   "$SQL_DIR/08_workouts_publication.sql"

echo ""
echo "=== Готово ==="
echo "Проверить publications:"
echo "  SELECT * FROM pg_publication;"
echo "Проверить tables:"
echo "  SELECT * FROM pg_publication_tables;"


