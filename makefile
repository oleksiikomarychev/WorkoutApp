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
	build-gateway build-rpe build-exercises build-user-max build-workouts build-plans build-agent \
	push-gateway push-rpe push-exercises push-user-max push-workouts push-plans push-agent

REGISTRY ?= docker.io/oleksiikomarychev
TAG ?= latest

# Build images
build-gateway:
	docker build -t $(REGISTRY)/workoutapp-gateway:$(TAG) ./gateway

build-rpe:
	docker build -t $(REGISTRY)/workoutapp-rpe-service:$(TAG) ./services/rpe-service

build-exercises:
	docker build -t $(REGISTRY)/workoutapp-exercises-service:$(TAG) ./services/exercises-service

build-user-max:
	docker build -t $(REGISTRY)/workoutapp-user-max-service:$(TAG) ./services/user-max-service

build-workouts:
	docker build -t $(REGISTRY)/workoutapp-workouts-service:$(TAG) ./services/workouts-service

build-plans:
	docker build -t $(REGISTRY)/workoutapp-plans-service:$(TAG) ./services/plans-service

build-agent:
	docker build -t $(REGISTRY)/workoutapp-agent-service:$(TAG) ./services/agent-service

build-all: build-gateway build-rpe build-exercises build-user-max build-workouts build-plans build-agent

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

push-all: push-gateway push-rpe push-exercises push-user-max push-workouts push-plans push-agent

# Build and push
release: build-all push-all
