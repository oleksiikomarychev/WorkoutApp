import asyncio
import logging
import sys
from concurrent import futures
from pathlib import Path

import grpc
from grpc_health.v1 import health_pb2, health_pb2_grpc

# Add proto_gen to path for imports
proto_gen_path = Path(__file__).parent.parent / "proto_gen"
sys.path.insert(0, str(proto_gen_path))

import workoutapp.plans.plans_pb2 as plans_pb2
import workoutapp.plans.plans_pb2_grpc as plans_pb2_grpc

from .dependencies import get_db
from .services.calendar_plan_service import CalendarPlanService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _proto_calendar_plan(plan):
    """Convert CalendarPlanResponse to proto CalendarPlan."""
    if not plan:
        return None
    
    mesocycles = []
    for m in plan.mesocycles or []:
        microcycles = []
        for mc in m.microcycles or []:
            plan_workouts = []
            for pw in mc.plan_workouts or []:
                exercises = []
                for pe in pw.exercises or []:
                    sets = []
                    for ps in pe.sets or []:
                        sets.append(
                            plans_pb2.PlanSet(
                                volume=ps.volume,
                                working_weight=ps.working_weight,
                                effort=ps.effort,
                                intensity=ps.intensity,
                            )
                        )
                    exercises.append(
                        plans_pb2.PlanExercise(
                            exercise_definition_id=pe.exercise_definition_id,
                            sets=sets,
                            notes=pe.notes or "",
                        )
                    )
                plan_workouts.append(
                    plans_pb2.PlanWorkout(
                        id=pw.id,
                        name=pw.name,
                        day_label=pw.day_label,
                        order_index=pw.order_index,
                        exercises=exercises,
                    )
                )
            microcycles.append(
                plans_pb2.Microcycle(
                    id=mc.id,
                    name=mc.name,
                    order_index=mc.order_index,
                    plan_workouts=plan_workouts,
                )
            )
        mesocycles.append(
            plans_pb2.Mesocycle(
                id=m.id,
                name=m.name,
                order_index=m.order_index,
                microcycles=microcycles,
            )
        )
    
    return plans_pb2.CalendarPlan(
        id=plan.id,
        name=plan.name,
        mesocycles=mesocycles,
    )


class PlansServicer(plans_pb2_grpc.PlansServiceServicer):
    """gRPC servicer for Plans service."""

    async def GetCalendarPlan(self, request, context):
        """Get a calendar plan by ID."""
        try:
            user_id = request.user_context.user_id if request.user_context else None
            
            async for db in get_db():
                plan = await CalendarPlanService.get_plan(db, request.calendar_plan_id, user_id)
                
                if not plan:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Calendar plan {request.calendar_plan_id} not found")
                    return plans_pb2.GetCalendarPlanResponse()
                
                proto_plan = _proto_calendar_plan(plan)
                return plans_pb2.GetCalendarPlanResponse(calendar_plan=proto_plan)
        except Exception as e:
            logger.error(f"Failed to get calendar plan {request.calendar_plan_id}: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plans_pb2.GetCalendarPlanResponse()

    async def ValidateMicrocycles(self, request, context):
        """Validate microcycle IDs."""
        try:
            user_id = request.user_context.user_id if request.user_context else None
            microcycle_ids = list(request.microcycle_ids) if request.microcycle_ids else []
            
            # Placeholder: implement actual validation logic
            # For now, return all IDs as valid
            valid_ids = microcycle_ids
            
            return plans_pb2.ValidateMicrocyclesResponse(valid_ids=valid_ids)
        except Exception as e:
            logger.error(f"Failed to validate microcycles: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plans_pb2.ValidateMicrocyclesResponse()

    async def GetParamsWorkout(self, request, context):
        """Get a params workout by ID."""
        try:
            user_id = request.user_context.user_id if request.user_context else None
            
            # Placeholder: implement actual params workout retrieval
            context.set_code(grpc.StatusCode.UNIMPLEMENTED)
            context.set_details("Params workout retrieval not yet implemented via gRPC")
            return plans_pb2.GetParamsWorkoutResponse()
        except Exception as e:
            logger.error(f"Failed to get params workout {request.params_workout_id}: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plans_pb2.GetParamsWorkoutResponse()


class HealthServicer(health_pb2_grpc.HealthServicer):
    """gRPC health check servicer."""

    async def Check(self, request, context):
        """Check service health."""
        return health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVING)

    async def Watch(self, request, context):
        """Watch service health (streaming)."""
        while True:
            yield health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVING)
            await asyncio.sleep(1)


async def serve(port: int = 50053):
    """Start gRPC server."""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    plans_pb2_grpc.add_PlansServiceServicer_to_server(PlansServicer(), server)
    health_pb2_grpc.add_HealthServicer_to_server(HealthServicer(), server)

    server.add_insecure_port(f"[::]:{port}")
    logger.info(f"Plans gRPC server started on port {port}")

    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
