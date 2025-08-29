from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from ..models.workout_session import WorkoutSession


class WorkoutSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, session_id: int) -> Optional[WorkoutSession]:
        return (
            self.db.query(WorkoutSession)
            .filter(WorkoutSession.id == session_id)
            .first()
        )

    def get_active_for_workout(self, workout_id: int) -> Optional[WorkoutSession]:
        return (
            self.db.query(WorkoutSession)
            .filter(
                WorkoutSession.workout_id == workout_id,
                WorkoutSession.status == "active",
            )
            .first()
        )

    def list_for_workout(self, workout_id: int) -> List[WorkoutSession]:
        return (
            self.db.query(WorkoutSession)
            .filter(WorkoutSession.workout_id == workout_id)
            .order_by(WorkoutSession.started_at.desc())
            .all()
        )

    def create_for_workout(self, workout_id: int) -> WorkoutSession:
        ws = WorkoutSession(
            workout_id=workout_id,
            started_at=datetime.utcnow(),
            status="active",
            progress={},
        )
        self.db.add(ws)
        self.db.commit()
        self.db.refresh(ws)
        return ws

    def update_progress(
        self, session: WorkoutSession, instance_id: int, set_id: int, completed: bool
    ) -> WorkoutSession:
        progress = dict(session.progress or {})
        completed_map = dict(progress.get("completed") or {})
        key = str(instance_id)
        arr = list(completed_map.get(key) or [])
        if completed:
            if set_id not in arr:
                arr.append(set_id)
        else:
            arr = [x for x in arr if x != set_id]
        completed_map[key] = arr
        progress["completed"] = completed_map
        session.progress = progress
        flag_modified(session, "progress")
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def finish(
        self,
        session: WorkoutSession,
        cancelled: bool = False,
        *,
        device_source: str | None = None,
        hr_avg: int | None = None,
        hr_max: int | None = None,
        hydration_liters: float | None = None,
        mood: str | None = None,
        injury_flags: dict | None = None,
    ) -> WorkoutSession:
        if not session.ended_at:
            session.ended_at = datetime.utcnow()
        session.status = "cancelled" if cancelled else "completed"
        try:
            session.duration_seconds = (
                int((session.ended_at - session.started_at).total_seconds())
                if session.started_at
                else None
            )
        except Exception:
            session.duration_seconds = None
        # Persist optional metrics if provided
        if device_source is not None:
            session.device_source = device_source
        if hr_avg is not None:
            session.hr_avg = hr_avg
        if hr_max is not None:
            session.hr_max = hr_max
        if hydration_liters is not None:
            session.hydration_liters = hydration_liters
        if mood is not None:
            session.mood = mood
        if injury_flags is not None:
            session.injury_flags = injury_flags
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session
