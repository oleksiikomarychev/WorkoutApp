#!/bin/bash
set -e

# Деплой Debezium коннекторов
# Использование:
#   ./deploy-connectors.sh                 # local, .env
#   ./deploy-connectors.sh prod            # prod, .env.example
#   ./deploy-connectors.sh local .env      # явный env файл
#   ./deploy-connectors.sh prod  .env.prod # явный env файл

ENV="${1:-local}"
ENV_FILE="${2:-}"

if [ -z "$ENV_FILE" ]; then
  if [ "$ENV" = "prod" ]; then
    ENV_FILE=".env.example"
  else
    ENV_FILE=".env"
  fi
fi

echo "=== Деплой Debezium коннекторов (среда: $ENV, env: $ENV_FILE) ==="

if [ ! -f "$ENV_FILE" ]; then
  echo "ОШИБКА: env файл не найден: $ENV_FILE"
  exit 1
fi

load_env_file() {
  local file="$1"
  while IFS= read -r line || [ -n "$line" ]; do
    line="$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    if [ -z "$line" ] || [[ "$line" == \#* ]]; then
      continue
    fi
    if [[ "$line" != *"="* ]]; then
      continue
    fi

    local key="${line%%=*}"
    local value="${line#*=}"

    key="$(echo "$key" | sed -e 's/[[:space:]]//g')"
    value="$(echo "$value" | sed -e 's/^[[:space:]]*//')"

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

CONNECT_URL="${DEBEZIUM_CONNECT_URL:-http://localhost:8083}"

# Путь к коннекторам
CONNECTORS_DIR="$(dirname "$0")/../debezium/connectors"

# Функция для парсинга DATABASE_URL
parse_db_url() {
    local url="$1"
    local prefix="$2"

    # normalize schemes: postgresql+asyncpg:// -> postgresql://
    url="${url/postgresql+asyncpg:\/\//postgresql:\/\/}"

    # postgresql://user:pass@host[:port]/dbname[?params]
    # Neon pooler URLs often omit the explicit port.
    local regex="postgresql://([^:]+):([^@]+)@([^:/]+)(:([0-9]+))?/([^?]+)"

    if [[ $url =~ $regex ]]; then
        eval "${prefix}_USER=${BASH_REMATCH[1]}"
        eval "${prefix}_PASS=${BASH_REMATCH[2]}"
        eval "${prefix}_HOST=${BASH_REMATCH[3]}"
        if [ -n "${BASH_REMATCH[5]}" ]; then
          eval "${prefix}_PORT=${BASH_REMATCH[5]}"
        else
          eval "${prefix}_PORT=5432"
        fi
        eval "${prefix}_NAME=${BASH_REMATCH[6]}"
    fi
}

require_env() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    echo ">>> ОШИБКА: переменная $name не задана в $ENV_FILE"
    exit 1
  fi
}

normalize_db_url_for_parser() {
  local url="$1"
  url="${url//\\/}"
  url="${url/postgresql+asyncpg:\/\//postgresql:\/\/}"
  echo "$url"
}

json_get_name() {
  local file="$1"
  python3 - "$file" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(data.get('name', ''))
PY
}

substitute_var() {
  local content="$1"
  local var="$2"
  local value="$3"
  # escape for sed replacement
  value=$(printf '%s' "$value" | sed -e 's/[\\&|/]/\\\\&/g')
  echo "$content" | sed "s|\${${var}}|${value}|g"
}

# Функция для деплоя коннектора
deploy_connector() {
    local connector_file="$1"
    local connector_name
    connector_name=$(json_get_name "$connector_file")
    if [ -z "$connector_name" ]; then
      echo ">>> ОШИБКА: не удалось прочитать name из $connector_file"
      return 1
    fi
    
    echo ">>> Деплой коннектора: $connector_name"
    
    # Читаем JSON и заменяем переменные
    local config=$(cat "$connector_file")
    
    # Заменяем переменные окружения
    config=$(substitute_var "$config" "DEBEZIUM_PASSWORD" "${DEBEZIUM_PASSWORD}")
    
    # Determine which DB URL is required for this connector
    local required_db_var=""
    local placeholder_prefix=""
    case "$connector_name" in
      accounts-connector)
        required_db_var="ACCOUNTS_DATABASE_URL"; placeholder_prefix="ACCOUNTS_DB" ;;
      agent-connector)
        required_db_var="AGENT_DATABASE_URL"; placeholder_prefix="AGENT_DB" ;;
      crm-connector)
        required_db_var="CRM_DATABASE_URL"; placeholder_prefix="CRM_DB" ;;
      exercises-connector)
        required_db_var="EXERCISES_DATABASE_URL"; placeholder_prefix="EXERCISES_DB" ;;
      user-max-connector)
        required_db_var="USER_MAX_DATABASE_URL"; placeholder_prefix="USER_MAX_DB" ;;
      plans-connector)
        required_db_var="PLANS_DATABASE_URL"; placeholder_prefix="PLANS_DB" ;;
      workouts-connector)
        required_db_var="WORKOUTS_DATABASE_URL"; placeholder_prefix="WORKOUTS_DB" ;;
      *)
        echo ">>> ОШИБКА: неизвестный коннектор $connector_name (не знаю какую DATABASE_URL использовать)"
        return 1
        ;;
    esac

    require_env "$required_db_var"

    # Reset parsed vars for safety
    unset ${placeholder_prefix}_HOST ${placeholder_prefix}_PORT ${placeholder_prefix}_NAME ${placeholder_prefix}_USER ${placeholder_prefix}_PASS

    local normalized_url
    normalized_url=$(normalize_db_url_for_parser "${!required_db_var}")
    parse_db_url "$normalized_url" "$placeholder_prefix"

    local host_var="${placeholder_prefix}_HOST"
    local port_var="${placeholder_prefix}_PORT"
    local name_var="${placeholder_prefix}_NAME"

    if [ -z "${!host_var:-}" ] || [ -z "${!port_var:-}" ] || [ -z "${!name_var:-}" ]; then
      echo ">>> ОШИБКА: не удалось распарсить $required_db_var (${!required_db_var})"
      return 1
    fi

    config=$(substitute_var "$config" "$host_var" "${!host_var}")
    config=$(substitute_var "$config" "$port_var" "${!port_var}")
    config=$(substitute_var "$config" "$name_var" "${!name_var}")
    
    # Удалить существующий коннектор (если есть)
    curl -s -X DELETE "$CONNECT_URL/connectors/$connector_name" > /dev/null 2>&1 || true
    
    # Создать коннектор
    local response=$(curl -s -X POST "$CONNECT_URL/connectors" \
        -H "Content-Type: application/json" \
        -d "$config")
    
    if echo "$response" | grep -q "error_code"; then
        echo ">>> ОШИБКА: $response"
        return 1
    else
        echo ">>> Успешно: $connector_name"
    fi
}

# Проверить доступность Debezium Connect
echo "Проверяю доступность Debezium Connect на $CONNECT_URL..."
for i in {1..30}; do
    if curl -s "$CONNECT_URL/" > /dev/null 2>&1; then
        echo "Debezium Connect доступен!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "ОШИБКА: Debezium Connect недоступен после 30 попыток"
        exit 1
    fi
    echo "Ожидание... ($i/30)"
    sleep 2
done

echo ""
echo "=== Деплой коннекторов ==="

# Деплой всех коннекторов
for connector_file in "$CONNECTORS_DIR"/*.json; do
    deploy_connector "$connector_file"
done

echo ""
echo "=== Проверка статуса коннекторов ==="
if command -v jq >/dev/null 2>&1; then
  curl -s "$CONNECT_URL/connectors" | jq '.'
elif command -v python3 >/dev/null 2>&1; then
  curl -s "$CONNECT_URL/connectors" | python3 -m json.tool
else
  curl -s "$CONNECT_URL/connectors"
fi

echo ""
echo "=== Готово ==="
echo ""
echo "Для проверки статуса конкретного коннектора:"
if command -v jq >/dev/null 2>&1; then
  echo "  curl $CONNECT_URL/connectors/<name>/status | jq"
elif command -v python3 >/dev/null 2>&1; then
  echo "  curl $CONNECT_URL/connectors/<name>/status | python3 -m json.tool"
else
  echo "  curl $CONNECT_URL/connectors/<name>/status"
fi
