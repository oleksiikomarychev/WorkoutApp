from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import AsyncIterator
from concurrent import futures
from pathlib import Path
from typing import Any

import grpc
from sqlalchemy import select

# Add proto_gen to sys.path for direct imports
proto_gen_path = Path(__file__).parent.parent / "proto_gen"
if proto_gen_path.exists() and str(proto_gen_path) not in sys.path:
    sys.path.insert(0, str(proto_gen_path))

try:
    from grpc_health.v1 import health_pb2, health_pb2_grpc
except ImportError:
    import health_pb2
    import health_pb2_grpc

try:
    import workoutapp.common.common_pb2 as common_pb2  # noqa: F401
except ImportError:
    try:
        import common_pb2 as common_pb2  # noqa: F401
    except ImportError:
        pass

try:
    import workoutapp.plans.plans_pb2 as plans_pb2
    import workoutapp.plans.plans_pb2_grpc as plans_pb2_grpc
except ImportError:
    import plans_pb2 as plans_pb2  # type: ignore[no-redef]
    import plans_pb2_grpc as plans_pb2_grpc  # type: ignore[no-redef]

from .config import settings
from .database import get_db
from .models.calendar import CalendarPlan, Mesocycle, Microcycle
from .services.calendar_plan_service import CalendarPlanService

logger = logging.getLogger(__name__)


def _proto_calendar_plan(plan: Any) -> plans_pb2.CalendarPlan | None:
    """Convert CalendarPlanResponse or model to proto CalendarPlan."""
    if not plan:
        return None

    mesocycles: list[plans_pb2.Mesocycle] = []
    for m in getattr(plan, "mesocycles", None) or []:
        microcycles: list[plans_pb2.Microcycle] = []
        for mc in getattr(m, "microcycles", None) or []:
            plan_workouts: list[plans_pb2.PlanWorkout] = []
            for pw in getattr(mc, "plan_workouts", None) or []:
                exercises: list[plans_pb2.PlanExercise] = []
                for pe in getattr(pw, "exercises", None) or []:
                    sets: list[plans_pb2.PlanSet] = []
                    for ps in getattr(pe, "sets", None) or []:
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
                            notes=getattr(pe, "notes", "") or "",
                        )
                    )
                plan_workouts.append(
                    plans_pb2.PlanWorkout(
                        id=pw.id,
                        name=getattr(pw, "name", None) or getattr(pw, "day_label", "") or "",
                        day_label=getattr(pw, "day_label", "") or "",
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

    async def GetCalendarPlan(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> plans_pb2.GetCalendarPlanResponse:
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
            return plans_pb2.GetCalendarPlanResponse()
        except Exception as e:
            logger.error(f"Failed to get calendar plan {request.calendar_plan_id}: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plans_pb2.GetCalendarPlanResponse()

    async def ValidateMicrocycles(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> plans_pb2.ValidateMicrocyclesResponse:
        """Validate microcycle IDs against the database."""
        try:
            user_id = request.user_context.user_id if request.user_context else None
            microcycle_ids = list(request.microcycle_ids) if request.microcycle_ids else []

            if not microcycle_ids:
                return plans_pb2.ValidateMicrocyclesResponse(valid_ids=[])

            async for db in get_db():
                stmt = (
                    select(Microcycle.id)
                    .join(Microcycle.mesocycle)
                    .join(Mesocycle.calendar_plan)
                    .where(Microcycle.id.in_(microcycle_ids))
                )
                if user_id:
                    stmt = stmt.where(CalendarPlan.user_id == user_id)

                result = await db.execute(stmt)
                valid_ids = [row[0] for row in result.all()]
                return plans_pb2.ValidateMicrocyclesResponse(valid_ids=valid_ids)
            return plans_pb2.ValidateMicrocyclesResponse(valid_ids=[])
        except Exception as e:
            logger.error(f"Failed to validate microcycles: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plans_pb2.ValidateMicrocyclesResponse()

    async def GetParamsWorkout(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> plans_pb2.GetParamsWorkoutResponse:
        """Get a params workout by ID."""
        try:
            context.set_code(grpc.StatusCode.UNIMPLEMENTED)
            context.set_details("Params workout retrieval not yet implemented via gRPC")
            return plans_pb2.GetParamsWorkoutResponse()
        except Exception as e:
            logger.error(f"Failed to get params workout: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plans_pb2.GetParamsWorkoutResponse()


class HealthServicer(health_pb2_grpc.HealthServicer):
    """gRPC health check servicer."""

    async def Check(self, request: Any, context: Any) -> health_pb2.HealthCheckResponse:
        """Check service health."""
        return health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVING)

    async def Watch(self, request: Any, context: Any) -> AsyncIterator[health_pb2.HealthCheckResponse]:
        """Watch service health (streaming)."""
        while True:
            yield health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVING)
            await asyncio.sleep(1)


async def serve(port: int | None = None) -> None:
    """Start gRPC server."""
    port = port or settings.GRPC_PORT
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    plans_pb2_grpc.add_PlansServiceServicer_to_server(PlansServicer(), server)
    health_pb2_grpc.add_HealthServicer_to_server(HealthServicer(), server)

    server.add_insecure_port(f"[::]:{port}")
    logger.info(f"Plans gRPC server started on port {port}")

    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    asyncio.run(serve())
