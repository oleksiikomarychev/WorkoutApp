#!/bin/bash
set -euo pipefail

# Инициализация ClickHouse таблиц
# Использование: ./init-clickhouse.sh [local|prod] [env_file]

ENV="${1:-local}"
ENV_FILE="${2:-.env}"

echo "=== Инициализация ClickHouse (среда: $ENV) ==="

# Загрузить переменные окружения
if [ ! -f "$ENV_FILE" ]; then
  echo "ОШИБКА: env файл не найден: $ENV_FILE"
  exit 1
fi

load_env_file() {
  local file="$1"
  while IFS= read -r line || [ -n "$line" ]; do
    if [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]]; then
      continue
    fi
    if [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=(.*)$ ]]; then
      local key="${BASH_REMATCH[1]}"
      local val="${BASH_REMATCH[2]}"
      val="${val%\r}"
      if [[ "$val" =~ ^\".*\"$ ]]; then
        val="${val:1:${#val}-2}"
      elif [[ "$val" =~ ^\'.*\'$ ]]; then
        val="${val:1:${#val}-2}"
      fi
      export "$key=$val"
    fi
  done < "$file"
}

load_env_file "$ENV_FILE"

# ClickHouse параметры
if [ "$ENV" == "prod" ]; then
    CH_HOST="${CLICKHOUSE_HOST:-localhost}"
    CH_PORT="${CLICKHOUSE_PORT:-9000}"
else
    CH_HOST="localhost"
    CH_PORT="9000"
fi

CH_USER="${CLICKHOUSE_USER:-default}"
CH_PASSWORD="${CLICKHOUSE_PASSWORD:-}"

# Путь к SQL файлам
SQL_DIR="$(dirname "$0")/../clickhouse/init"

# Функция для выполнения SQL файла
run_sql_file() {
    local sql_file="$1"
    local filename=$(basename "$sql_file")
    
    echo ">>> Выполняю $filename..."
    
    if [ -n "$CH_PASSWORD" ]; then
        docker exec -i clickhouse clickhouse-client \
            --user "$CH_USER" \
            --password "$CH_PASSWORD" \
            --multiquery < "$sql_file"
    else
        docker exec -i clickhouse clickhouse-client \
            --user "$CH_USER" \
            --multiquery < "$sql_file"
    fi
    
    echo ">>> Готово: $filename"
}

# Проверить доступность ClickHouse
echo "Проверяю доступность ClickHouse..."
for i in {1..30}; do
    if docker exec clickhouse clickhouse-client -q "SELECT 1" > /dev/null 2>&1; then
        echo "ClickHouse доступен!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "ОШИБКА: ClickHouse недоступен после 30 попыток"
        exit 1
    fi
    echo "Ожидание... ($i/30)"
    sleep 2
done

echo ""
echo "=== Выполнение SQL скриптов ==="

# Выполнить все SQL файлы по порядку
# Можно отключить refresh-скрипт (тяжёлые INSERT ... SELECT) через SKIP_REFRESH=1
for sql_file in $(ls -1 "$SQL_DIR"/*.sql | sort); do
    filename=$(basename "$sql_file")
    if [ "${SKIP_REFRESH:-0}" = "1" ] && [ "$filename" = "11_refresh_views.sql" ]; then
        echo ">>> Пропускаю $filename (SKIP_REFRESH=1)"
        continue
    fi
    run_sql_file "$sql_file"
done

echo ""
echo "=== Проверка созданных таблиц ==="

echo ""
echo "Raw таблицы:"
docker exec clickhouse clickhouse-client -q "SELECT name FROM system.tables WHERE database = 'raw' ORDER BY name" 2>/dev/null || echo "(база raw еще не создана)"

echo ""
echo "Analytics таблицы:"
docker exec clickhouse clickhouse-client -q "SELECT name FROM system.tables WHERE database = 'analytics' ORDER BY name" 2>/dev/null || echo "(база analytics еще не создана)"

echo ""
echo "=== Готово ==="
echo ""
echo "Для проверки данных:"
echo "  docker exec -it clickhouse clickhouse-client"
echo "  SELECT count() FROM raw.workouts;"
