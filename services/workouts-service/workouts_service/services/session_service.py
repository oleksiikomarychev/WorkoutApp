from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models import Workout, WorkoutSession
from ..exceptions import WorkoutNotFoundException, SessionNotFoundException, ActiveSessionNotFoundException
import logging

logger = logging.getLogger(__name__)

class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_workout_session(self, workout_id: int, started_at: datetime | None = None) -> WorkoutSession:
        result = await self.db.execute(select(Workout).filter(Workout.id == workout_id))
        workout = result.scalars().first()
        if not workout:
            raise WorkoutNotFoundException(workout_id)

        # If an active session exists, return it instead of creating duplicate
        result = await self.db.execute(
            select(WorkoutSession)
            .filter(WorkoutSession.workout_id == workout_id, WorkoutSession.status == "active")
        )
        active = result.scalars().first()
        if active:
            return active

        if started_at is None:
            started_at = datetime.now(timezone.utc)
        elif started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
            
        # Convert to naive UTC for database storage
        naive_started_at = started_at.replace(tzinfo=None)
        
        session = WorkoutSession(workout_id=workout_id, started_at=naive_started_at, status="active")
        self.db.add(session)
        # reflect in workout meta
        if not workout.started_at:
            workout.started_at = naive_started_at
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_active_session(self, workout_id: int) -> WorkoutSession:
        result = await self.db.execute(
            select(WorkoutSession)
            .filter(WorkoutSession.workout_id == workout_id, WorkoutSession.status == "active")
        )
        session = result.scalars().first()
        if not session:
            raise ActiveSessionNotFoundException(workout_id)
        return session

    async def get_session_history(self, workout_id: int) -> list[WorkoutSession]:
        result = await self.db.execute(
            select(WorkoutSession)
            .filter(WorkoutSession.workout_id == workout_id)
            .order_by(WorkoutSession.id.desc())
        )
        return result.scalars().all()

    async def finish_session(self, session_id: int) -> WorkoutSession:
        result = await self.db.execute(select(WorkoutSession).filter(WorkoutSession.id == session_id))
        session = result.scalars().first()
        if not session:
            raise SessionNotFoundException(session_id)
        if session.status == "finished":
            return session
        
        # Use naive UTC datetime for database
        finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.status = "finished"
        session.finished_at = finished_at
        
        # Mark workout completed
        result = await self.db.execute(select(Workout).filter(Workout.id == session.workout_id))
        workout = result.scalars().first()
        if workout:
            if not workout.completed_at:
                workout.completed_at = finished_at
            workout.status = "completed"
            
        await self.db.commit()
        await self.db.refresh(session)
        
        return session
