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

## Agent behavior

The Flutter client sends screen context and messages over `/chat/ws`. The agent service keeps that context for the WebSocket session and dispatches each message to a command handler, the plan-generation state machine, or screen-specific tools.

```text
Flutter screen + selection
          │ context / message
          ▼
       /chat/ws
          │
          ▼
   EventDispatcher ── commands / apply events ──► mass edit / schedule shift
          │
          ├── plan generation mode ──► conversation_graph.py
          │
          └── ordinary message
                    │
                    ▼
             ScreenToolsBuilder
                    │ available tools for this screen
                    ▼
               tool_agent.py ──► tool_result_dispatcher.py ──► WebSocket result
                    │ no handled tool call
                    ▼
               plain chat reply
```

### Tools by screen

| Screen | Available tools |
| --- | --- |
| `active_plan` | Schedule shift, applied-plan mass edit, plan analysis |
| `coach_athlete_plan` | Applied-plan mass edit, plan analysis, athlete history |
| `plan_details` | Plan macros analysis and management, plan analysis |
| `user_profile` | Completed-workout analysis |
| `calendar_plans` | Plan recommendations from the plans in screen context |
| `user_max`, `analytics` | Strength-data analysis |
| `coach_athletes` | Coach portfolio analysis |

`ScreenToolsBuilder` builds this list from the `screen`, `selection`, and `entities` in session context. The tool agent decides whether to call one of those tools. If no tool result handles the message, the plain chat handler generates a reply.

### Conversation modes and result flow

- `@fsm_plan_generator` switches the session to multi-turn plan generation in `conversation_graph.py`. When generation finishes, the session returns to chat mode.
- `/mass-edit` and `/mass_edit` are handled as explicit commands before the ordinary message path.
- An applied-plan mass edit generates a structured command, validates it, and sends it to the workouts service. The response is sent to the client as a `mass_edit_result` WebSocket event; preview and apply modes are supported.

For example, a mass-edit request from `active_plan` follows this path:

```text
screen context → ScreenToolsBuilder → applied_plan_mass_edit tool
             → structured edit command → workouts service
             → mass_edit_result WebSocket event → client
```

The entry point is `services/agent-service/agent_service/main.py`. Routing and response handling are in `services/agent-service/agent_service/services/event_dispatcher.py`, `screen_tools_builder.py`, `message_handlers.py`, and `tool_result_dispatcher.py`.
