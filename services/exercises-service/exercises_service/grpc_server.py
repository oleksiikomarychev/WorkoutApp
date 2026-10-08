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

import exercises_pb2 as exercises_pb2
import exercises_pb2_grpc as exercises_pb2_grpc

from .dependencies import get_db
from .redis_client import get_redis_client
from .services.exercise_definition_service import ExerciseDefinitionService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _proto_exercise_definition(definition):
    """Convert ExerciseListResponse to proto ExerciseDefinition."""
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


def _proto_exercise_instance(instance):
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
    """gRPC servicer for Exercises service."""

    async def GetExercise(self, request, context):
        """Get a single exercise definition by ID."""
        try:
            async for db in get_db():
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
            logger.error(f"Failed to get exercise {request.exercise_id}: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return exercises_pb2.GetExerciseResponse()

    async def GetExerciseDefinitions(self, request, context):
        """Get multiple exercise definitions by IDs."""
        try:
            ids = list(request.ids) if request.ids else []
            
            async for db in get_db():
                redis_client = await get_redis_client()
                service = ExerciseDefinitionService(db, redis_client)
                
                definitions = await service.list_definitions(ids=ids)
                
                proto_definitions = [_proto_exercise_definition(d) for d in definitions]
                return exercises_pb2.GetExerciseDefinitionsResponse(definitions=proto_definitions)
        except Exception as e:
            logger.error(f"Failed to get exercise definitions: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return exercises_pb2.GetExerciseDefinitionsResponse()

    async def CreateExerciseInstances(self, request, context):
        """Create exercise instances (placeholder - not fully implemented)."""
        try:
            # This would need the exercise instances service implementation
            # For now, return the instances as-is
            context.set_code(grpc.StatusCode.UNIMPLEMENTED)
            context.set_details("Exercise instances creation not yet implemented via gRPC")
            return exercises_pb2.CreateExerciseInstancesResponse()
        except Exception as e:
            logger.error(f"Failed to create exercise instances: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return exercises_pb2.CreateExerciseInstancesResponse()

    async def GetExerciseInstances(self, request, context):
        """Get exercise instances for a workout (placeholder)."""
        try:
            # This would need the exercise instances service implementation
            context.set_code(grpc.StatusCode.UNIMPLEMENTED)
            context.set_details("Exercise instances retrieval not yet implemented via gRPC")
            return exercises_pb2.GetExerciseInstancesResponse()
        except Exception as e:
            logger.error(f"Failed to get exercise instances: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return exercises_pb2.GetExerciseInstancesResponse()


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


async def serve(port: int = 50052):
    """Start gRPC server."""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    exercises_pb2_grpc.add_ExercisesServiceServicer_to_server(ExercisesServicer(), server)
    health_pb2_grpc.add_HealthServicer_to_server(HealthServicer(), server)

    server.add_insecure_port(f"[::]:{port}")
    logger.info(f"Exercises gRPC server started on port {port}")

    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
