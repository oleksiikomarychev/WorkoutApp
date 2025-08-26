from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.workout import Workout
from app.models.workout_session import WorkoutSession
from app.repositories.workout_session_repository import WorkoutSessionRepository


class WorkoutSessionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = WorkoutSessionRepository(db)

    def start_session(self, workout_id: int) -> WorkoutSession:
        # ensure workout exists
        workout = self.db.get(Workout, workout_id)
        if not workout:
            raise ValueError("Workout not found")
        # return active if exists
        existing = self.repo.get_active_for_workout(workout_id)
        if existing:
            return existing
        return self.repo.create_for_workout(workout_id)

    def get_active_session(self, workout_id: int) -> Optional[WorkoutSession]:
        return self.repo.get_active_for_workout(workout_id)

    def list_sessions(self, workout_id: int) -> List[WorkoutSession]:
        # ensure workout exists (optional for list)
        return self.repo.list_for_workout(workout_id)

    def update_progress(self, session_id: int, instance_id: int, set_id: int, completed: bool) -> WorkoutSession:
        session = self.repo.get(session_id)
        if not session:
            raise ValueError("Session not found")
        if session.status != "active":
            raise ValueError("Session is not active")
        return self.repo.update_progress(session, instance_id, set_id, completed)

    def finish_session(
        self,
        session_id: int,
        cancelled: bool = False,
        mark_workout_completed: bool = False,
        *,
        device_source: str | None = None,
        hr_avg: int | None = None,
        hr_max: int | None = None,
        hydration_liters: float | None = None,
        mood: str | None = None,
        injury_flags: dict | None = None,
    ) -> WorkoutSession:
        session = self.repo.get(session_id)
        if not session:
            raise ValueError("Session not found")
        session = self.repo.finish(
            session,
            cancelled,
            device_source=device_source,
            hr_avg=hr_avg,
            hr_max=hr_max,
            hydration_liters=hydration_liters,
            mood=mood,
            injury_flags=injury_flags,
        )
        if mark_workout_completed and not cancelled:
            workout = self.db.get(Workout, session.workout_id)
            if workout:
                workout.completed_at = workout.completed_at or datetime.utcnow()
                self.db.add(workout)
                self.db.commit()
                self.db.refresh(workout)
        return session
