"""gRPC server for RPE calculations."""

from collections.abc import AsyncIterator
import asyncio
from concurrent import futures
import logging
from pathlib import Path
import sys
from typing import Any

import grpc

# Add proto_gen to path for imports
proto_gen_path = Path(__file__).parent.parent / "proto_gen"
if str(proto_gen_path) not in sys.path:
    sys.path.insert(0, str(proto_gen_path))

try:
    from grpc_health.v1 import health_pb2, health_pb2_grpc
except ImportError:
    import health_pb2  # type: ignore[no-redef]
    import health_pb2_grpc  # type: ignore[no-redef]

try:
    import workoutapp.common.common_pb2 as common_pb2  # noqa: F401, E402
except ImportError:
    try:
        import common_pb2 as common_pb2  # noqa: F401, E402
    except ImportError:
        pass

try:
    import workoutapp.rpe.rpe_pb2 as rpe_pb2  # noqa: E402
    import workoutapp.rpe.rpe_pb2_grpc as rpe_pb2_grpc  # noqa: E402
except ImportError:
    import rpe_pb2 as rpe_pb2  # type: ignore[no-redef]  # noqa: E402
    import rpe_pb2_grpc as rpe_pb2_grpc  # type: ignore[no-redef]  # noqa: E402

from .calculation import calculate_rpe_set_values, get_rpe_table  # noqa: E402
from .config import settings  # noqa: E402
from .rpc import get_effective_max  # noqa: E402

logger = logging.getLogger("rpe_service.grpc")


class RPEServicer(rpe_pb2_grpc.RPEServiceServicer):
    """gRPC servicer for RPE calculations."""

    async def Compute(
        self,
        request: rpe_pb2.RPEComputeRequest,
        context: grpc.aio.ServicerContext,
    ) -> rpe_pb2.RPEComputeResponse:
        """Compute RPE-based weight calculation via gRPC."""
        try:
            intensity = request.intensity if request.HasField("intensity") else None
            effort = request.effort if request.HasField("effort") else None
            volume = request.volume if request.HasField("volume") else None

            user_id: str | None = None
            if request.HasField("user_context") and request.user_context.user_id:
                user_id = request.user_context.user_id

            max_weight: float | None = request.max_weight if request.HasField("max_weight") else None
            if request.user_max_id:
                try:
                    fetched_max = await get_effective_max(request.user_max_id, user_id=user_id)
                    max_weight = fetched_max
                except Exception as e:
                    logger.warning("Failed to get effective max for user_max_id=%s: %s", request.user_max_id, e)

            table = get_rpe_table()
            rounding_step = request.rounding_step if request.rounding_step > 0 else 2.5
            rounding_mode = request.rounding_mode or "nearest"

            _, _, _, weight = calculate_rpe_set_values(
                table=table,
                intensity=intensity,
                effort=effort,
                volume=volume,
                max_weight=max_weight,
                rounding_step=rounding_step,
                rounding_mode=rounding_mode,
            )

            return rpe_pb2.RPEComputeResponse(
                computed_weight=weight,
                suggested_weight=weight,
                message="RPE calculation completed successfully",
            )

        except Exception as e:
            error_msg = (
                f"RPE calculation failed: {str(e)}. "
                f"Input: intensity={request.intensity}, volume={request.volume}, effort={request.effort}. "
                "This combination may not exist in the RPE table. "
                "Valid ranges: 90-100%→1-3 reps, 80-89%→3-6 reps, 70-79%→6-10 reps, "
                "60-69%→10-20 reps, 50-59%→15-25 reps."
            )
            logger.error("%s", error_msg)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(error_msg)
            return rpe_pb2.RPEComputeResponse()


class HealthServicer(health_pb2_grpc.HealthServicer):
    """gRPC health check servicer."""

    async def Check(
        self,
        request: Any,
        context: grpc.aio.ServicerContext,
    ) -> health_pb2.HealthCheckResponse:
        """Check service health status."""
        return health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVING)

    async def Watch(
        self,
        request: Any,
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterator[health_pb2.HealthCheckResponse]:
        """Watch service health stream."""
        while True:
            yield health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVING)
            await asyncio.sleep(1)


async def serve(port: int = settings.GRPC_PORT) -> None:
    """Start gRPC server."""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    rpe_pb2_grpc.add_RPEServiceServicer_to_server(RPEServicer(), server)
    health_pb2_grpc.add_HealthServicer_to_server(HealthServicer(), server)

    server.add_insecure_port(f"[::]:{port}")
    logger.info("RPE gRPC server started on port %d", port)

    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    asyncio.run(serve())

