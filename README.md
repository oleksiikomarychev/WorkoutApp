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

<table>
  <tr>
    <td><img src="gateway/gateway_app/image/Screenshot%202025-09-22%20at%2019.09.42.png" alt="Screenshot 1" width="320"></td>
    <td><img src="gateway/gateway_app/image/Screenshot%202025-09-22%20at%2019.09.50.png" alt="Screenshot 2" width="320"></td>
  </tr>
  <tr>
    <td><img src="gateway/gateway_app/image/Screenshot%202025-09-22%20at%2019.09.54.png" alt="Screenshot 3" width="320"></td>
    <td><img src="gateway/gateway_app/image/Screenshot%202025-09-22%20at%2019.10.09.png" alt="Screenshot 4" width="320"></td>
  </tr>
</table>

## Architecture

- Backend: FastAPI microservices, SQLAlchemy ORM, Pydantic v2, Alembic (migrations)
- API Gateway (FastAPI) proxies all client traffic
- Frontend: Flutter (Material 3)
- Layers: `routers/` (HTTP), `services/` (business logic), `repositories/` (data)
- RPE/1RM logic: proper intensity tables and true 1RM calculation from real sets

## Authentication & User Scoping

All services use user-scoped data isolation via the **`X-User-Id` header**:

- **Header Name**: `X-User-Id` (case-insensitive matching in code)
- **Required**: All authenticated endpoints require this header; missing header returns `401 Unauthorized`
- **Propagation**: Services forward `X-User-Id` to downstream service calls (e.g., workouts-service → exercises-service, agent-service → plans-service)
- **Isolation**: Each service filters queries by `user_id` to ensure users only access their own data

### Services with User Scoping

- **exercises-service**: `exercise_instances` filtered by `user_id`
- **user-max-service**: `user_maxes` filtered by `user_id`
- **workouts-service**: `workouts`, `sessions`, etc. filtered by `user_id`
- **plans-service**: `calendar_plans` filtered by `user_id`
- **agent-service**: `generated_plans` filtered by `user_id`

### Gateway (Future)

The API Gateway will validate bearer tokens and inject the `X-User-Id` header for internal service calls. Services trust this header only from the gateway network.

## AI Agent Flow

The agent-service implements a **screen-aware agentic system** where available AI tools are dynamically determined by the user's current app screen.

### Architecture Overview

```
┌─────────────────┐     WebSocket      ┌──────────────────────────────────────┐
│   Flutter App   │◄──────────────────►│           agent-service              │
│  (screen state) │                    │                                      │
└────────┬────────┘                    │  ┌────────────────────────────────┐  │
         │                             │  │     ScreenToolsBuilder         │  │
         │ screen="active_plan"        │  │  screen → available tools      │  │
         │ entities={...}              │  └───────────────┬────────────────┘  │
         │ selection={...}             │                  │                   │
         ▼                             │                  ▼                   │
┌─────────────────┐                    │  ┌────────────────────────────────┐  │
│ Session Context │───────────────────►│  │   LangChain Tool Agent         │  │
│                 │                    │  │  (Gemini 2.5 Flash)            │  │
└─────────────────┘                    │  │  - selects tool                │  │
                                       │  │  - extracts arguments          │  │
                                       │  │  - executes handler            │  │
                                       │  └────────────────────────────────┘  │
                                       └──────────────────────────────────────┘
```

### Screen-Dependent Tools

| Screen | Available Tools | Use Cases |
|--------|-----------------|-----------|
| `active_plan` | `schedule_shift`, `mass_edit`, `plan_analysis` | Shift dates, bulk edit sets/weights, analyze plan |
| `coach_athlete_plan` | `mass_edit`, `plan_analysis`, `athlete_history` | Edit athlete's plan, analyze progress |
| `plan_details` | `macros_analysis`, `manage_macros`, `plan_analysis` | Create/explain automation rules |
| `user_profile` | `completed_workouts_analysis` | Analyze training history |
| `calendar_plans` | `recommend_calendar_plans` | Find/compare plans by criteria |
| `user_max` / `analytics` | `user_max_analysis` | Analyze strength records |
| `coach_athletes` | `coach_portfolio_analysis` | Portfolio-wide athlete insights |

### Key Components

- **Entry Point**: `services/agent-service/agent_service/main.py` — WebSocket `/chat/ws` endpoint with event dispatcher
- **Tool Router**: `services/agent-service/agent_service/services/screen_tools_builder.py` — maps screen to `ToolSpec` list
- **Agent Executor**: `services/agent-service/agent_service/services/tool_agent.py` — LangChain agent with Gemini LLM
- **LLM Wrapper**: `services/agent-service/agent_service/services/llm_wrapper.py` — structured JSON output with schema validation

### Conversation Modes

1. **FSM Mode** (`conversation_graph.py`) — multi-turn dialogue for plan generation with state machine
2. **Tool Agent Mode** (`tool_agent.py`) — single-turn tool execution based on screen context
3. **Plain Chat Mode** — direct LLM response when no tool is needed

### Example Flow: Mass Edit

```
User: "Add 2 sets to all chest exercises from next week"
  │
  ▼
ScreenToolsBuilder.build(screen="active_plan")
  │ → [schedule_shift, mass_edit, plan_analysis]
  ▼
run_tools_agent() → LLM selects mass_edit tool
  │
  ▼
generate_applied_mass_edit_command() → LLM generates JSON:
  │   {
  │     "filter": {"scheduled_from": "2025-01-06", "exercise_definition_ids": [101,102]},
  │     "actions": {"increase_volume_by": 2}
  │   }
  ▼
JSON Schema validation → apply to workouts-service
  │
  ▼
WebSocket notification → UI update
```

### Integrations

- **plans-service**: Plan persistence and macro rules storage
- **workouts-service**: Mass edit execution, workout data
- **exercises-service**: Exercise definitions lookup
- **user-max-service**: Strength analytics with hybrid statistical + LLM analysis