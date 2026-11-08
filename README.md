![WorkoutApp preview](assets/readme-preview.gif)

# WorkoutApp

Flutter client backed by a FastAPI gateway and separate Python services. This README records the repository's component boundaries and communication paths.

## Components

| Path | Responsibility |
| --- | --- |
| `flutter_app/` | Flutter client |
| `gateway/` | HTTP entry point for the client; proxies requests to services |
| `services/` | Accounts, exercises, plans, workouts, strength calculations, CRM, and agent services |
| `social-service/`, `messaging-service/`, `webhook-dispatcher/` | Social data, messaging, and webhook delivery |
| `analytics/` | CDC configuration and scripts for the analytics pipeline |
| `proto/` | Protocol Buffer contracts and generated Python stubs for gRPC calls |

## Communication

- The Flutter client calls the FastAPI gateway. Gateway routes use HTTP or gRPC to reach services; gRPC clients and contracts are in `gateway/gateway_app/grpc_clients.py` and `proto/`.
- The agent service exposes a WebSocket endpoint at `/chat/ws`. Its `ScreenToolsBuilder` selects tools from the current screen context; conversation state and tool execution live in separate modules under `services/agent-service/agent_service/services/`.
- Redis backs asynchronous Celery work in the plans, workouts, and agent services. Service and infrastructure wiring is defined in `docker-compose.yml`.

## Data and deployment

- Database-backed services keep persistence code and Alembic migrations in their service directories.
- The analytics pipeline moves PostgreSQL changes through Debezium and Kafka into ClickHouse; its setup is documented in `analytics/README.md`.
- `docker-compose.yml` defines the local service topology. `docker-compose.prod.yml` contains the production composition.
