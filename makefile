.PHONY: run migrate makemigrations superuser sync pre-commit

run:
	python3 -m uvicorn app.main:app --reload

pre-commit:
	pre-commit run --all-files

makemigrations:
	docker compose exec exercises-service alembic upgrade head
	docker compose exec workouts-service alembic upgrade head
	docker compose exec plans-service alembic upgrade head
	docker compose exec user-max-service alembic upgrade head
	docker compose exec agent-service alembic upgrade head
	docker compose exec accounts-service alembic upgrade head
	docker compose exec crm-service alembic upgrade head
	docker compose exec exercises-service alembic revision --autogenerate -m "exercises: update models"
	docker compose exec workouts-service alembic revision --autogenerate -m "workouts: update models"
	docker compose exec plans-service alembic revision --autogenerate -m "plans: update models"
	docker compose exec user-max-service alembic revision --autogenerate -m "user-max: update models"
	docker compose exec agent-service alembic revision --autogenerate -m "agent: update models"
	docker compose exec accounts-service alembic revision --autogenerate -m "accounts: update models"
	docker compose exec crm-service alembic revision --autogenerate -m "crm: update models"

superuser:
	python manage.py createsuperuser

activate:
	bash -c "source .venv/bin/activate"

alembic:
	alembic revision --autogenerate -m "update_models"

migrate:
	docker compose exec exercises-service alembic upgrade head
	docker compose exec workouts-service alembic upgrade head
	docker compose exec plans-service alembic upgrade head
	docker compose exec user-max-service alembic upgrade head
	docker compose exec agent-service alembic upgrade head
	docker compose exec accounts-service alembic upgrade head
	docker compose exec crm-service alembic upgrade head

sync:
	make makemigrations
	make migrate

# Docker release tooling
.PHONY: build-all push-all release \
	build-gateway build-rpe build-exercises build-user-max build-workouts build-plans build-agent build-accounts build-crm \
	push-gateway push-rpe push-exercises push-user-max push-workouts push-plans push-agent push-accounts push-crm

REGISTRY ?= docker.io/oleksiikomarychev
TAG ?= latest

PLATFORMS ?= linux/amd64,linux/arm64

# Build images
build-gateway:
	docker build -t $(REGISTRY)/workoutapp-gateway:$(TAG) -f gateway/Dockerfile .

build-rpe:
	docker build -t $(REGISTRY)/workoutapp-rpe-service:$(TAG) -f services/rpe-service/Dockerfile .

build-exercises:
	docker build -t $(REGISTRY)/workoutapp-exercises-service:$(TAG) -f services/exercises-service/Dockerfile .

build-user-max:
	docker build -t $(REGISTRY)/workoutapp-user-max-service:$(TAG) -f services/user-max-service/Dockerfile .

build-workouts:
	docker build -t $(REGISTRY)/workoutapp-workouts-service:$(TAG) -f services/workouts-service/Dockerfile .

build-plans:
	docker build -t $(REGISTRY)/workoutapp-plans-service:$(TAG) -f services/plans-service/Dockerfile .

build-agent:
	docker build -t $(REGISTRY)/workoutapp-agent-service:$(TAG) -f services/agent-service/Dockerfile .

build-accounts:
	docker build -t $(REGISTRY)/workoutapp-accounts-service:$(TAG) -f services/accounts-service/Dockerfile .

build-crm:
	docker build -t $(REGISTRY)/workoutapp-crm-service:$(TAG) -f services/crm-service/Dockerfile .

build-all: build-gateway build-rpe build-exercises build-user-max build-workouts build-plans build-agent build-accounts build-crm

.PHONY: release-all

release-gateway:
	docker buildx build --platform $(PLATFORMS) --push -t $(REGISTRY)/workoutapp-gateway:$(TAG) -f gateway/Dockerfile .

release-rpe:
	docker buildx build --platform $(PLATFORMS) --push -t $(REGISTRY)/workoutapp-rpe-service:$(TAG) -f ./services/rpe-service/Dockerfile .

release-exercises:
	docker buildx build --platform $(PLATFORMS) --push -t $(REGISTRY)/workoutapp-exercises-service:$(TAG) -f services/exercises-service/Dockerfile .

release-user-max:
	docker buildx build --platform $(PLATFORMS) --push -t $(REGISTRY)/workoutapp-user-max-service:$(TAG) -f services/user-max-service/Dockerfile .

release-workouts:
	docker buildx build --platform $(PLATFORMS) --push -t $(REGISTRY)/workoutapp-workouts-service:$(TAG) -f services/workouts-service/Dockerfile .

release-plans:
	docker buildx build --platform $(PLATFORMS) --push -t $(REGISTRY)/workoutapp-plans-service:$(TAG) -f services/plans-service/Dockerfile .

release-agent:
	docker buildx build --platform $(PLATFORMS) --push -t $(REGISTRY)/workoutapp-agent-service:$(TAG) -f services/agent-service/Dockerfile .

release-accounts:
	docker buildx build --platform $(PLATFORMS) --push -t $(REGISTRY)/workoutapp-accounts-service:$(TAG) -f services/accounts-service/Dockerfile .

release-crm:
	docker buildx build --platform $(PLATFORMS) --push -t $(REGISTRY)/workoutapp-crm-service:$(TAG) -f services/crm-service/Dockerfile .

release-all: release-gateway release-rpe release-exercises release-user-max release-workouts release-plans release-agent release-accounts release-crm

# Push images
push-gateway:
	docker push $(REGISTRY)/workoutapp-gateway:$(TAG)

push-rpe:
	docker push $(REGISTRY)/workoutapp-rpe-service:$(TAG)

push-exercises:
	docker push $(REGISTRY)/workoutapp-exercises-service:$(TAG)

push-user-max:
	docker push $(REGISTRY)/workoutapp-user-max-service:$(TAG)

push-workouts:
	docker push $(REGISTRY)/workoutapp-workouts-service:$(TAG)

push-plans:
	docker push $(REGISTRY)/workoutapp-plans-service:$(TAG)

push-agent:
	docker push $(REGISTRY)/workoutapp-agent-service:$(TAG)

push-accounts:
	docker push $(REGISTRY)/workoutapp-accounts-service:$(TAG)

push-crm:
	docker push $(REGISTRY)/workoutapp-crm-service:$(TAG)

push-all: push-gateway push-rpe push-exercises push-user-max push-workouts push-plans push-agent push-accounts push-crm

# Build and push
release: release-all

# === CDC / Analytics (Postgres -> Debezium -> Kafka -> ClickHouse) ===
.PHONY: analytics-up analytics-down analytics-setup analytics-status analytics-logs

# Запустить CDC/Analytics стек (локально)
analytics-up:
	docker compose --profile analytics up -d

# Остановить CDC/Analytics стек
analytics-down:
	docker compose --profile analytics down

# Полная настройка CDC пайплайна (после analytics-up)
analytics-setup:
	@echo "=== Настройка CDC пайплайна ==="
	@echo ""
	@echo "1. Настройте Postgres (выполните SQL вручную):"
	./analytics/scripts/setup-postgres.sh
	@echo ""
	@echo "2. Задеплойте Debezium коннекторы:"
	./analytics/scripts/deploy-connectors.sh
	@echo ""
	@echo "3. Инициализируйте ClickHouse таблицы:"
	./analytics/scripts/init-clickhouse.sh

# Проверить статус CDC пайплайна
analytics-status:
	./analytics/scripts/check-status.sh

# Логи CDC компонентов
analytics-logs:
	docker compose --profile analytics logs -f --tail=100

# Только деплой коннекторов
analytics-deploy-connectors:
	./analytics/scripts/deploy-connectors.sh

# Только инициализация ClickHouse
analytics-init-clickhouse:
	./analytics/scripts/init-clickhouse.sh

# Открыть ClickHouse клиент
analytics-clickhouse-cli:
	docker exec -it clickhouse clickhouse-client

# Открыть Kafka UI (http://localhost:8084)
analytics-kafka-ui:
	@echo "Kafka UI: http://localhost:8084"
	@open http://localhost:8084 2>/dev/null || xdg-open http://localhost:8084 2>/dev/null || echo "Open http://localhost:8084 in browser"

# Production: Запустить CDC/Analytics стек
analytics-up-prod:
	docker compose -f docker-compose.prod.yml --profile analytics up -d

# Production: Остановить CDC/Analytics стек
analytics-down-prod:
	docker compose -f docker-compose.prod.yml --profile analytics down

# Production: Полная настройка
analytics-setup-prod:
	./analytics/scripts/setup-postgres.sh prod
	./analytics/scripts/deploy-connectors.sh prod
	./analytics/scripts/init-clickhouse.sh prod
