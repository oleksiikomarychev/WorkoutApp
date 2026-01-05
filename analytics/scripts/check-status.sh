#!/bin/bash

# Проверка статуса CDC пайплайна
# Использование: ./check-status.sh

echo "=== Статус CDC пайплайна ==="
echo ""

# Проверить Kafka
echo "--- Kafka ---"
if docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1; then
    echo "✓ Kafka: работает"
    
    echo "  Топики:"
    docker exec kafka kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null | grep -E "^(accounts|agent|crm|exercises|user-max|plans|workouts)-db" | head -20
    TOPIC_COUNT=$(docker exec kafka kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null | grep -E "^(accounts|agent|crm|exercises|user-max|plans|workouts)-db" | wc -l)
    echo "  Всего CDC топиков: $TOPIC_COUNT"
else
    echo "✗ Kafka: не работает"
fi

echo ""

# Проверить Debezium Connect
echo "--- Debezium Connect ---"
CONNECT_URL="http://localhost:8083"
if curl -s "$CONNECT_URL/" > /dev/null 2>&1; then
    echo "✓ Debezium Connect: работает"
    
    echo "  Коннекторы:"
    CONNECTORS=$(curl -s "$CONNECT_URL/connectors" 2>/dev/null)
    echo "$CONNECTORS" | jq -r '.[]' 2>/dev/null | while read connector; do
        STATUS=$(curl -s "$CONNECT_URL/connectors/$connector/status" 2>/dev/null)
        STATE=$(echo "$STATUS" | jq -r '.connector.state' 2>/dev/null)
        TASKS=$(echo "$STATUS" | jq -r '.tasks[0].state' 2>/dev/null)
        
        if [ "$STATE" == "RUNNING" ] && [ "$TASKS" == "RUNNING" ]; then
            echo "    ✓ $connector: RUNNING"
        else
            echo "    ✗ $connector: $STATE / tasks: $TASKS"
        fi
    done
else
    echo "✗ Debezium Connect: не работает"
fi

echo ""

# Проверить ClickHouse
echo "--- ClickHouse ---"
if docker exec clickhouse clickhouse-client -q "SELECT 1" > /dev/null 2>&1; then
    echo "✓ ClickHouse: работает"
    
    echo "  Raw таблицы с данными:"
    docker exec clickhouse clickhouse-client -q "
        SELECT 
            database || '.' || name AS table_name,
            formatReadableQuantity(total_rows) AS rows
        FROM system.tables 
        WHERE database = 'raw' 
          AND total_rows > 0
        ORDER BY total_rows DESC
        LIMIT 10
    " 2>/dev/null || echo "    (нет данных)"
    
    echo ""
    echo "  Analytics таблицы с данными:"
    docker exec clickhouse clickhouse-client -q "
        SELECT 
            database || '.' || name AS table_name,
            formatReadableQuantity(total_rows) AS rows
        FROM system.tables 
        WHERE database = 'analytics' 
          AND total_rows > 0
        ORDER BY total_rows DESC
        LIMIT 10
    " 2>/dev/null || echo "    (нет данных)"
else
    echo "✗ ClickHouse: не работает"
fi

echo ""
echo "=== Готово ==="
