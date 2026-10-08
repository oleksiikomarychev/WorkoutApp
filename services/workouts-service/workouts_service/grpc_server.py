import asyncio
import logging
import re
import sys
from concurrent import futures
from datetime import datetime
from pathlib import Path

import grpc

# Add proto_gen to path for imports
proto_gen_path = Path(__file__).parent.parent / "proto_gen"
sys.path.insert(0, str(proto_gen_path))

import common_pb2 as common_pb2
import exercises_pb2 as exercises_pb2
import workouts_pb2 as workouts_pb2
import workouts_pb2_grpc as workouts_pb2_grpc

from workouts_service.database import get_db
from workouts_service.services.rpc_client import PlansServiceRPC, get_exercise_by_id
from workouts_service.services.workout_service import WorkoutService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PLANS_SERVICE_URL = "http://plans-service:8005"


def _proto_exercise_instance(workout_exercise):
    """Convert WorkoutExercise to proto ExerciseInstance."""
    if not workout_exercise:
        return None
    
    sets = []
    for s in workout_exercise.sets or []:
        sets.append(
            exercises_pb2.Set(
                id=s.id,
                reps=s.volume,
                working_weight=s.working_weight,
                rpe=s.effort,
                effort=s.effort,
                effort_type="RPE",
                intensity=s.intensity,
                order=s.order_index,
            )
        )
    
    return exercises_pb2.ExerciseInstance(
        id=workout_exercise.id,
        exercise_list_id=workout_exercise.exercise_id,
        workout_id=workout_exercise.workout_id,
        sets=sets,
        notes=workout_exercise.notes or "",
        order=workout_exercise.order,
        user_max_id=None,
    )


def _proto_workout(workout):
    """Convert Workout model to proto Workout."""
    if not workout:
        return None
    
    exercise_instances = []
    for we in workout.exercises or []:
        exercise_instances.append(_proto_exercise_instance(we))
    
    return workouts_pb2.Workout(
        id=workout.id,
        name=workout.name,
        status=workout.status or "pending",
        workout_type=workout.workout_type or "manual",
        started_at=workout.started_at.isoformat() if workout.started_at else None,
        finished_at=workout.completed_at.isoformat() if workout.completed_at else None,
        applied_plan_id=workout.applied_plan_id,
        plan_order_index=workout.plan_order_index,
        exercise_instances=exercise_instances,
    )


def _proto_workout_session(session):
    """Convert WorkoutSession model to proto WorkoutSession."""
    if not session:
        return None
    
    exercise_instances = []
    # Note: Session may not have exercise_instances loaded, handle this case
    exercises = None
    if hasattr(session, "exercises") and session.exercises:
        exercises = session.exercises
    elif hasattr(session, "workout") and session.workout and getattr(session.workout, "exercises", None):
        exercises = session.workout.exercises

    if exercises:
        for we in exercises or []:
            exercise_instances.append(_proto_exercise_instance(we))
    
    # Ensure UTC timezone suffix for naive datetimes
    started_at_str = None
    if session.started_at and isinstance(session.started_at, datetime):
        started_at_str = session.started_at.isoformat()
        if started_at_str and not started_at_str.endswith('Z') and not re.search(r'[+-]\d{2}:\d{2}$', started_at_str):
            started_at_str = f"{started_at_str}Z"
    # Filter out invalid strings
    if started_at_str and (not started_at_str.strip() or started_at_str.strip() == 'Z'):
        started_at_str = None
    
    finished_at_str = None
    if session.finished_at and isinstance(session.finished_at, datetime):
        finished_at_str = session.finished_at.isoformat()
        if finished_at_str and not finished_at_str.endswith('Z') and not re.search(r'[+-]\d{2}:\d{2}$', finished_at_str):
            finished_at_str = f"{finished_at_str}Z"
    # Filter out invalid strings
    if finished_at_str and (not finished_at_str.strip() or finished_at_str.strip() == 'Z'):
        finished_at_str = None
    
    # Build proto message with only valid fields
    kwargs = {
        "id": session.id,
        "workout_id": session.workout_id,
        "status": session.status or "active",
        "exercise_instances": exercise_instances,
    }
    if started_at_str:
        kwargs["started_at"] = started_at_str
    if finished_at_str:
        kwargs["finished_at"] = finished_at_str
    
    return workouts_pb2.WorkoutSession(**kwargs)


class WorkoutServicer(workouts_pb2_grpc.WorkoutServiceServicer):
    """gRPC servicer for Workouts service."""

    async def CreateWorkout(self, request, context):
        """Create a new workout."""
        try:
            user_id = request.user_context.user_id if request.user_context else None
            
            async for db in get_db():
                plans_rpc = PlansServiceRPC(base_url=PLANS_SERVICE_URL)
                exercises_rpc = get_exercise_by_id
                service = WorkoutService(db, plans_rpc, exercises_rpc, user_id)
                
                # Convert proto workout to schema
                from workouts_service.schemas.workout import WorkoutCreate
                
                workout_data = {
                    "name": request.workout.name,
                    "status": request.workout.status,
                    "workout_type": request.workout.workout_type,
                    "applied_plan_id": request.workout.applied_plan_id if request.workout.HasField("applied_plan_id") else None,
                    "plan_order_index": request.workout.plan_order_index if request.workout.HasField("plan_order_index") else None,
                }
                
                payload = WorkoutCreate(**workout_data)
                workout = await service.create_workout(payload)
                
                proto_workout = _proto_workout(workout)
                return workouts_pb2.CreateWorkoutResponse(workout=proto_workout)
        except Exception as e:
            logger.error(f"Failed to create workout: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return workouts_pb2.CreateWorkoutResponse()

    async def GetWorkout(self, request, context):
        """Get a workout by ID."""
        try:
            user_id = request.user_context.user_id if request.user_context else None
            
            async for db in get_db():
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload

                from workouts_service.models import Workout
                
                result = await db.execute(
                    select(Workout)
                    .options(selectinload(Workout.exercises).selectinload(WorkoutExercise.sets))
                    .where(Workout.id == request.workout_id, Workout.user_id == user_id)
                )
                workout = result.scalar_one_or_none()
                
                if not workout:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Workout {request.workout_id} not found")
                    return workouts_pb2.GetWorkoutResponse()
                
                proto_workout = _proto_workout(workout)
                return workouts_pb2.GetWorkoutResponse(workout=proto_workout)
        except Exception as e:
            logger.error(f"Failed to get workout {request.workout_id}: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return workouts_pb2.GetWorkoutResponse()

    async def UpdateWorkout(self, request, context):
        """Update a workout."""
        try:
            user_id = request.user_context.user_id if request.user_context else None
            
            async for db in get_db():
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload

                from workouts_service.models import Workout
                
                result = await db.execute(
                    select(Workout)
                    .options(selectinload(Workout.exercises).selectinload(WorkoutExercise.sets))
                    .where(Workout.id == request.workout_id, Workout.user_id == user_id)
                )
                workout = result.scalar_one_or_none()
                
                if not workout:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Workout {request.workout_id} not found")
                    return workouts_pb2.UpdateWorkoutResponse()
                
                # Update fields
                if request.workout.name:
                    workout.name = request.workout.name
                if request.workout.status:
                    workout.status = request.workout.status
                if request.workout.HasField("applied_plan_id"):
                    workout.applied_plan_id = request.workout.applied_plan_id
                if request.workout.HasField("plan_order_index"):
                    workout.plan_order_index = request.workout.plan_order_index
                
                await db.commit()
                await db.refresh(workout)
                
                proto_workout = _proto_workout(workout)
                return workouts_pb2.UpdateWorkoutResponse(workout=proto_workout)
        except Exception as e:
            logger.error(f"Failed to update workout {request.workout_id}: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return workouts_pb2.UpdateWorkoutResponse()

    async def ListWorkouts(self, request, context):
        """List workouts for a user."""
        try:
            user_id = request.user_context.user_id if request.user_context else None
            skip = request.pagination.skip if request.pagination else 0
            limit = request.pagination.limit if request.pagination else 50
            
            async for db in get_db():
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload

                from workouts_service.models import Workout, WorkoutExercise
                
                result = await db.execute(
                    select(Workout)
                    .options(selectinload(Workout.exercises).selectinload(WorkoutExercise.sets))
                    .where(Workout.user_id == user_id)
                    .order_by(Workout.id.desc())
                    .offset(skip)
                    .limit(limit)
                )
                workouts = result.scalars().all()
                
                proto_workouts = [_proto_workout(w) for w in workouts]
                
                pagination = common_pb2.PaginationResponse(
                    total=len(proto_workouts),
                    skip=skip,
                    limit=limit,
                )
                
                return workouts_pb2.ListWorkoutsResponse(workouts=proto_workouts, pagination=pagination)
        except Exception as e:
            logger.error(f"Failed to list workouts: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return workouts_pb2.ListWorkoutsResponse()

    async def GetNextWorkout(self, request, context):
        """Get the next scheduled workout."""
        try:
            user_id = request.user_context.user_id if request.user_context else None
            
            async for db in get_db():
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload

                from workouts_service.models import Workout, WorkoutExercise
                
                result = await db.execute(
                    select(Workout)
                    .options(selectinload(Workout.exercises).selectinload(WorkoutExercise.sets))
                    .where(Workout.user_id == user_id, Workout.status == "pending")
                    .order_by(Workout.scheduled_for.asc())
                    .limit(1)
                )
                workout = result.scalar_one_or_none()
                
                if not workout:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details("No next workout found")
                    return workouts_pb2.GetNextWorkoutResponse()
                
                proto_workout = _proto_workout(workout)
                return workouts_pb2.GetNextWorkoutResponse(workout=proto_workout)
        except Exception as e:
            logger.error(f"Failed to get next workout: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return workouts_pb2.GetNextWorkoutResponse()

    async def StartWorkout(self, request, context):
        """Start a workout."""
        try:
            user_id = request.user_context.user_id if request.user_context else None
            
            async for db in get_db():
                from datetime import datetime

                from sqlalchemy import select
                from sqlalchemy.orm import selectinload

                from workouts_service.models import Workout, WorkoutExercise
                
                result = await db.execute(
                    select(Workout)
                    .options(selectinload(Workout.exercises).selectinload(WorkoutExercise.sets))
                    .where(Workout.id == request.workout_id, Workout.user_id == user_id)
                )
                workout = result.scalar_one_or_none()
                
                if not workout:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Workout {request.workout_id} not found")
                    return workouts_pb2.StartWorkoutResponse()
                
                workout.status = "in_progress"
                workout.started_at = datetime.utcnow()
                await db.commit()
                await db.refresh(workout)
                
                proto_workout = _proto_workout(workout)
                return workouts_pb2.StartWorkoutResponse(workout=proto_workout)
        except Exception as e:
            logger.error(f"Failed to start workout {request.workout_id}: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return workouts_pb2.StartWorkoutResponse()

    async def FinishWorkout(self, request, context):
        """Finish a workout."""
        try:
            user_id = request.user_context.user_id if request.user_context else None
            
            async for db in get_db():
                from datetime import datetime

                from sqlalchemy import select
                from sqlalchemy.orm import selectinload

                from workouts_service.models import Workout, WorkoutExercise
                
                result = await db.execute(
                    select(Workout)
                    .options(selectinload(Workout.exercises).selectinload(WorkoutExercise.sets))
                    .where(Workout.id == request.workout_id, Workout.user_id == user_id)
                )
                workout = result.scalar_one_or_none()
                
                if not workout:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Workout {request.workout_id} not found")
                    return workouts_pb2.FinishWorkoutResponse()
                
                workout.status = "completed"
                workout.completed_at = datetime.utcnow()
                await db.commit()
                await db.refresh(workout)
                
                proto_workout = _proto_workout(workout)
                return workouts_pb2.FinishWorkoutResponse(workout=proto_workout)
        except Exception as e:
            logger.error(f"Failed to finish workout {request.workout_id}: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return workouts_pb2.FinishWorkoutResponse()

    async def ReplaceExercise(self, request, context):
        """Replace exercise ID in a workout."""
        try:
            user_id = request.user_context.user_id if request.user_context else None
            
            async for db in get_db():
                from sqlalchemy import update

                from workouts_service.models import WorkoutExercise
                
                # Update all exercise instances with old_exercise_id to new_exercise_id
                result = await db.execute(
                    update(WorkoutExercise)
                    .where(
                        WorkoutExercise.workout_id == request.workout_id,
                        WorkoutExercise.user_id == user_id,
                        WorkoutExercise.exercise_id == request.old_exercise_id,
                    )
                    .values(exercise_id=request.new_exercise_id)
                )
                updated_count = result.rowcount
                await db.commit()
                
                return workouts_pb2.ReplaceExerciseResponse(updated_count=updated_count)
        except Exception as e:
            logger.error(f"Failed to replace exercise in workout {request.workout_id}: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return workouts_pb2.ReplaceExerciseResponse()

    async def GetWorkoutWithDetails(self, request, context):
        """Get a workout with exercise instances."""
        try:
            user_id = request.user_context.user_id if request.user_context else None
            
            async for db in get_db():
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload

                from workouts_service.models import Workout, WorkoutExercise
                
                result = await db.execute(
                    select(Workout)
                    .options(selectinload(Workout.exercises).selectinload(WorkoutExercise.sets))
                    .where(Workout.id == request.workout_id, Workout.user_id == user_id)
                )
                workout = result.scalar_one_or_none()
                
                if not workout:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Workout {request.workout_id} not found")
                    return workouts_pb2.GetWorkoutWithDetailsResponse()
                
                proto_workout = _proto_workout(workout)
                return workouts_pb2.GetWorkoutWithDetailsResponse(workout=proto_workout)
        except Exception as e:
            logger.error(f"Failed to get workout with details {request.workout_id}: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return workouts_pb2.GetWorkoutWithDetailsResponse()

    async def GetActiveSession(self, request, context):
        """Get active workout session."""
        try:
            user_id = request.user_context.user_id if request.user_context else None
            
            async for db in get_db():
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload

                from workouts_service.models import Workout, WorkoutExercise, WorkoutSession
                
                result = await db.execute(
                    select(WorkoutSession)
                    .options(
                        selectinload(WorkoutSession.workout)
                        .selectinload(Workout.exercises)
                        .selectinload(WorkoutExercise.sets)
                    )
                    .where(
                        WorkoutSession.workout_id == request.workout_id,
                        WorkoutSession.user_id == user_id,
                        WorkoutSession.status == "active"
                    )
                )
                session = result.scalar_one_or_none()
                
                if not session:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"No active session for workout {request.workout_id}")
                    return workouts_pb2.GetActiveSessionResponse()
                
                proto_session = _proto_workout_session(session)
                return workouts_pb2.GetActiveSessionResponse(session=proto_session)
        except Exception as e:
            logger.error(f"Failed to get active session for workout {request.workout_id}: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return workouts_pb2.GetActiveSessionResponse()

    async def GetSessionHistory(self, request, context):
        """Get workout session history."""
        try:
            user_id = request.user_context.user_id if request.user_context else None
            
            async for db in get_db():
                from sqlalchemy import select

                from workouts_service.models import WorkoutSession
                
                result = await db.execute(
                    select(WorkoutSession)
                    .where(
                        WorkoutSession.workout_id == request.workout_id,
                        WorkoutSession.user_id == user_id
                    )
                    .order_by(WorkoutSession.started_at.desc())
                )
                sessions = result.scalars().all()
                
                proto_sessions = [_proto_workout_session(s) for s in sessions]
                return workouts_pb2.GetSessionHistoryResponse(sessions=proto_sessions)
        except Exception as e:
            logger.error(f"Failed to get session history for workout {request.workout_id}: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return workouts_pb2.GetSessionHistoryResponse()

    async def ListAllSessions(self, request, context):
        """List all workout sessions for user."""
        try:
            user_id = request.user_context.user_id if request.user_context else None
            
            async for db in get_db():
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload

                from workouts_service.models import Workout, WorkoutExercise, WorkoutSession
                
                result = await db.execute(
                    select(WorkoutSession)
                    .options(selectinload(WorkoutSession.workout).selectinload(Workout.exercises).selectinload(WorkoutExercise.sets))
                    .where(WorkoutSession.user_id == user_id)
                    .order_by(WorkoutSession.started_at.desc())
                )
                sessions = result.scalars().all()
                
                proto_sessions = [_proto_workout_session(s) for s in sessions]
                return workouts_pb2.ListAllSessionsResponse(sessions=proto_sessions)
        except Exception as e:
            logger.error(f"Failed to list all sessions: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return workouts_pb2.ListAllSessionsResponse()


# class HealthServicer(health_pb2_grpc.HealthServicer):
#     """gRPC health check servicer."""
#
#     async def Check(self, request, context):
#         """Check service health."""
#         return health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVING)
#
#     async def Watch(self, request, context):
#         """Watch service health (streaming)."""
#         while True:
#             yield health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVING)
#             await asyncio.sleep(1)


async def serve(port: int = 50054):
    """Start gRPC server."""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    workouts_pb2_grpc.add_WorkoutServiceServicer_to_server(WorkoutServicer(), server)
    # health_pb2_grpc.add_HealthServicer_to_server(HealthServicer(), server)

    server.add_insecure_port(f"0.0.0.0:{port}")
    logger.info(f"Workouts gRPC server started on port {port}")

    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
