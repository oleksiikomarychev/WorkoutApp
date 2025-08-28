# WorkoutApp — Train Smarter. Progress Faster.

Modern strength training tracker that turns your plan into actionable daily workouts. Built with FastAPI + Flutter, designed for lifters and coaches who want data‑driven progress.

## Features

- User Management (Athletes, Trainers)
- Exercise Library and Tracking
- Progression Templates
- Workout Creation and Logging
- Strength Testing
- Performance Analytics

## Highlights

- Bold, fast mobile UI focused on set execution and clarity
- RPE engine with true 1RM derivation for accurate intensity prescriptions
- Readiness slider: scale weights (and optionally reps) with smart rounding
- Calendar plan wizard with meso/micro cycles and per-week day layout
- Clean architecture backend: routers → services → repositories

## Screenshots

Note: images are stored in `app/config/images/`.

<table>
  <tr>
    <td><img src="app/config/images/Screenshot%202025-08-26%20at%2020.18.46.png" alt="Home" width="320"></td>
    <td><img src="app/config/images/Screenshot%202025-08-26%20at%2020.14.25.png" alt="Workout Detail" width="320"></td>
    <td><img src="app/config/images/Screenshot%202025-08-26%20at%2020.20.26.png" alt="Plan Wizard" width="320"></td>
  </tr>
  <tr>
    <td><img src="app/config/images/Screenshot%202025-08-26%20at%2020.20.32.png" alt="Exercises" width="320"></td>
    <td><img src="app/config/images/Screenshot%202025-08-26%20at%2020.19.32.png" alt="Active Plan" width="320"></td>
    <td><img src="app/config/images/Screenshot%202025-08-25%20at%2018.58.42.png" alt="Lists" width="320"></td>
  </tr>
  
</table>

## Architecture

- Backend: FastAPI microservices, SQLAlchemy ORM, Pydantic v2, Alembic (migrations)
- API Gateway (FastAPI) proxies all client traffic
- Frontend: Flutter (Material 3)
- Layers: `routers/` (HTTP), `services/` (business logic), `repositories/` (data)
- RPE/1RM logic: proper intensity tables and true 1RM calculation from real sets

## Project Structure

- `gateway/`: API gateway (`gateway_app/main.py`)
- `services/`:
  - `exercises-service/`
  - `plans-service/`
  - `user-max-service/`
  - `workouts-service/`
  - `rpe-service/`
- `flutter_app/`: Mobile client
- `docker-compose.yml`: Local multi-service orchestration
- `pyproject.toml`: Legacy root app definition (not required for microservices run)

## Environment (.env)

The stack uses per-service databases. By default, containers use SQLite files in their own volumes. Configure via `.env` in repo root (picked by `docker-compose.yml`):

```env
# SQLite defaults inside containers (recommended for local/dev)
EXERCISES_DATABASE_URL="sqlite:////app/data/exercises.db"
USER_MAX_DATABASE_URL="sqlite:////app/data/user_max.db"
WORKOUTS_DATABASE_URL="sqlite:////app/data/workouts.db"
PLANS_DATABASE_URL="sqlite:////app/data/plans.db"

# Optional: switch any service to Postgres
# EXERCISES_DATABASE_URL="postgresql://user:pass@localhost:5432/exercises_db"
# USER_MAX_DATABASE_URL="postgresql://user:pass@localhost:5432/user_max_db"
# WORKOUTS_DATABASE_URL="postgresql://user:pass@localhost:5432/workouts_db"
# PLANS_DATABASE_URL="postgresql://user:pass@localhost:5432/plans_db"

# Gateway config
CORS_ORIGINS="*"
MONO_WORKOUTS=true
```

Notes:
- In Docker, absolute SQLite paths start with `sqlite:////app/data/...` (four slashes).
- For running services directly on host (without Docker), you can use relative SQLite paths like `sqlite:///./data/plans.db` and ensure the `data/` folder exists.

## Running (Docker, recommended)
 
1. Create `.env` as above.
2. Start the stack:
    ```bash
    docker compose up --build
    ```
3. API base URL (gateway): `http://localhost:8010`
    - Docs: `http://localhost:8010/docs`
    - Example routes via gateway:
      - `GET /api/v1/rpe`
      - `GET /api/v1/exercises`
      - `GET /api/v1/user-max`
      - `GET /api/v1/plans/calendar-plans`
 
Services also expose health on their own ports (8001..8005), but clients should call the gateway.

## Local development with Poetry
 
We use Poetry instead of pip/requirements.txt. Each service has its own `pyproject.toml`.
 
- Install Poetry (one time):
    ```bash
    curl -sSL https://install.python-poetry.org | python3 -
    ```
 
- Install deps and run a service (example: plans-service):
    ```bash
    cd services/plans-service
    poetry install
    # ensure .env has PLANS_DATABASE_URL (e.g., sqlite:///./data/plans.db)
    poetry run uvicorn plans_service.main:app --reload --host 0.0.0.0 --port 8005
    ```
 
- Gateway locally:
    ```bash
    cd gateway
    poetry install
    poetry run uvicorn gateway_app.main:app --reload --host 0.0.0.0 --port 8000
    # Then access http://localhost:8000 (Docker maps gateway to 8010 when containerized)
    ```
 
Repeat similarly for other services (`exercises_service`, `user_max_service`, `workouts_service`, `rpe_service`) using their module paths and ports from `docker-compose.yml`.

## Migrations
 
Each microservice owns its migrations. Example (exercises-service):
```bash
cd services/exercises-service
poetry run alembic upgrade head
# after model changes
poetry run alembic revision -m "add_new_table"
poetry run alembic upgrade head
```

## Flutter client
 
- The client should point to the gateway base URL (e.g., `http://127.0.0.1:8010`).
- Wizard/classic flows hit `/api/v1/plans/*`, `/api/v1/exercises/*`, `/api/v1/user-max*`, `/api/v1/workouts*` via gateway.

## Contribution notes
 
- Avoid cross-service DB coupling; integrate over HTTP via gateway.
- Use SQLite in dev; switch to Postgres via `.env` when needed.
- Poetry is the standard dependency manager across services.
