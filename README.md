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