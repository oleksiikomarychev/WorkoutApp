from __future__ import annotations

import asyncio
import logging
import sys
from concurrent import futures
from pathlib import Path
from typing import Any

import grpc

# Add proto_gen to path for proto imports
proto_gen_path = Path(__file__).parent.parent / "proto_gen"
sys.path.insert(0, str(proto_gen_path))

try:
    from grpc_health.v1 import health_pb2, health_pb2_grpc
except ImportError:
    import health_pb2  # type: ignore[no-redef]
    import health_pb2_grpc  # type: ignore[no-redef]

import common_pb2  # noqa: F401, E402
import exercises_pb2  # noqa: E402
import exercises_pb2_grpc  # noqa: E402

from .database import AsyncSessionLocal  # noqa: E402
from .redis_client import get_redis_client  # noqa: E402
from .services.exercise_definition_service import ExerciseDefinitionService  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _proto_exercise_definition(definition: Any) -> exercises_pb2.ExerciseDefinition | None:
    """Convert ExerciseListResponse or model to proto ExerciseDefinition."""
    if not definition:
        return None

    return exercises_pb2.ExerciseDefinition(
        id=definition.id,
        name=definition.name,
        muscle_group=definition.muscle_group or "",
        equipment=definition.equipment or "",
        description="",
        media_image=definition.image_url or "",
        media_gif=definition.gif_url or "",
    )


def _proto_exercise_instance(instance: Any) -> exercises_pb2.ExerciseInstance | None:
    """Convert exercise instance to proto ExerciseInstance."""
    if not instance:
        return None

    sets = []
    for s in instance.sets or []:
        sets.append(
            exercises_pb2.Set(
                id=s.id,
                reps=s.reps,
                working_weight=s.working_weight,
                rpe=s.rpe,
                effort=s.effort,
                effort_type=s.effort_type or "RPE",
                intensity=s.intensity,
                order=s.order,
            )
        )

    return exercises_pb2.ExerciseInstance(
        id=instance.id,
        exercise_list_id=instance.exercise_list_id,
        workout_id=instance.workout_id,
        sets=sets,
        notes=instance.notes or "",
        order=instance.order,
        user_max_id=instance.user_max_id,
    )


class ExercisesServicer(exercises_pb2_grpc.ExercisesServiceServicer):
    """gRPC servicer implementing ExercisesService definition."""

    async def GetExercise(self, request: Any, context: grpc.aio.ServicerContext) -> exercises_pb2.GetExerciseResponse:
        """Get a single exercise definition by ID."""
        try:
            async with AsyncSessionLocal() as db:
                redis_client = await get_redis_client()
                service = ExerciseDefinitionService(db, redis_client)

                definition = await service.get_definition(request.exercise_id)

                if not definition:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Exercise definition {request.exercise_id} not found")
                    return exercises_pb2.GetExerciseResponse()

                proto_def = _proto_exercise_definition(definition)
                return exercises_pb2.GetExerciseResponse(exercise=proto_def)
        except Exception as e:
            logger.error("Failed to get exercise %s: %s", request.exercise_id, str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return exercises_pb2.GetExerciseResponse()

    async def GetExerciseDefinitions(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> exercises_pb2.GetExerciseDefinitionsResponse:
        """Get multiple exercise definitions by IDs."""
        try:
            ids = list(request.ids) if request.ids else []

            async with AsyncSessionLocal() as db:
                redis_client = await get_redis_client()
                service = ExerciseDefinitionService(db, redis_client)

                definitions = await service.list_definitions(ids=ids)

                proto_definitions = [_proto_exercise_definition(d) for d in definitions]
                return exercises_pb2.GetExerciseDefinitionsResponse(definitions=proto_definitions)
        except Exception as e:
            logger.error("Failed to get exercise definitions: %s", str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return exercises_pb2.GetExerciseDefinitionsResponse()

    async def CreateExerciseInstances(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> exercises_pb2.CreateExerciseInstancesResponse:
        """Create exercise instances (managed by workouts-service)."""
        try:
            context.set_code(grpc.StatusCode.UNIMPLEMENTED)
            context.set_details("Exercise instances are managed in workouts-service")
            return exercises_pb2.CreateExerciseInstancesResponse()
        except Exception as e:
            logger.error("Failed to create exercise instances: %s", str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return exercises_pb2.CreateExerciseInstancesResponse()

    async def GetExerciseInstances(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> exercises_pb2.GetExerciseInstancesResponse:
        """Get exercise instances (managed by workouts-service)."""
        try:
            context.set_code(grpc.StatusCode.UNIMPLEMENTED)
            context.set_details("Exercise instances are managed in workouts-service")
            return exercises_pb2.GetExerciseInstancesResponse()
        except Exception as e:
            logger.error("Failed to get exercise instances: %s", str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return exercises_pb2.GetExerciseInstancesResponse()


class HealthServicer(health_pb2_grpc.HealthServicer):
    """gRPC standard health check servicer."""

    async def Check(self, request: Any, context: grpc.aio.ServicerContext) -> health_pb2.HealthCheckResponse:
        """Check service health."""
        return health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVING)

    async def Watch(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        """Watch service health stream."""
        while True:
            yield health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVING)
            await asyncio.sleep(1)


async def serve(port: int = 50052) -> None:
    """Start gRPC server."""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    exercises_pb2_grpc.add_ExercisesServiceServicer_to_server(ExercisesServicer(), server)
    health_pb2_grpc.add_HealthServicer_to_server(HealthServicer(), server)

    server.add_insecure_port(f"[::]:{port}")
    logger.info("Exercises gRPC server started on port %s", port)

    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
