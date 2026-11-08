"""gRPC server for RPE calculations."""

import asyncio
import logging
import sys
from collections.abc import AsyncIterator
from concurrent import futures
from pathlib import Path
from typing import Any

import grpc  # type: ignore[import-untyped]

from .calculation import calculate_rpe_set_values, get_rpe_table
from .config import settings
from .rpc import get_effective_max

# Add proto_gen to path for imports
proto_gen_path = Path(__file__).resolve().parent.parent / "proto_gen"
if str(proto_gen_path) not in sys.path:
    sys.path.insert(0, str(proto_gen_path))

try:
    from grpc_health.v1 import health_pb2, health_pb2_grpc  # type: ignore[import-untyped]  # noqa: E402
except ImportError:
    import health_pb2  # type: ignore[no-redef, import-not-found]  # noqa: E402
    import health_pb2_grpc  # type: ignore[no-redef, import-not-found]  # noqa: E402

# Ensure common_pb2 is registered in descriptor pool before rpe_pb2
try:
    import workoutapp.common.common_pb2 as common_pb2  # type: ignore[import-not-found]  # noqa: E402, F401
except ImportError:
    try:
        import common_pb2 as common_pb2  # type: ignore[import-not-found]  # noqa: E402, F401
    except ImportError:
        pass

try:
    import workoutapp.rpe.rpe_pb2 as rpe_pb2  # type: ignore[import-not-found]  # noqa: E402
    import workoutapp.rpe.rpe_pb2_grpc as rpe_pb2_grpc  # type: ignore[import-not-found]  # noqa: E402
except ImportError:
    import rpe_pb2 as rpe_pb2  # type: ignore[no-redef, import-not-found]  # noqa: E402
    import rpe_pb2_grpc as rpe_pb2_grpc  # type: ignore[no-redef, import-not-found]  # noqa: E402

logger = logging.getLogger("rpe_service.grpc")


def _has_field(msg: Any, field_name: str) -> bool:
    """Safely check if a protobuf message has an optional field set."""
    try:
        return bool(msg.HasField(field_name))
    except (ValueError, AttributeError):
        return getattr(msg, field_name, None) is not None


class RPEServicer(rpe_pb2_grpc.RPEServiceServicer):
    """gRPC servicer for RPE calculations."""

    async def Compute(
        self,
        request: rpe_pb2.RPEComputeRequest,
        context: grpc.aio.ServicerContext,
    ) -> rpe_pb2.RPEComputeResponse:
        """Compute RPE-based weight calculation via gRPC."""
        try:
            intensity = request.intensity if _has_field(request, "intensity") else None
            effort = request.effort if _has_field(request, "effort") else None
            volume = request.volume if _has_field(request, "volume") else None

            user_id: str | None = None
            if _has_field(request, "user_context") and getattr(request.user_context, "user_id", None):
                user_id = request.user_context.user_id

            max_weight: float | None = request.max_weight if _has_field(request, "max_weight") else None
            user_max_id: int | None = request.user_max_id if _has_field(request, "user_max_id") else None

            if user_max_id:
                try:
                    fetched_max = await get_effective_max(user_max_id, user_id=user_id)
                    max_weight = fetched_max
                except Exception as e:
                    logger.warning("Failed to get effective max for user_max_id=%s: %s", user_max_id, e)

            table = get_rpe_table()
            rounding_step = request.rounding_step if request.rounding_step > 0 else 2.5
            rounding_mode = (request.rounding_mode or "nearest").lower().strip()
            if rounding_mode not in ("nearest", "floor", "ceil"):
                rounding_mode = "nearest"

            _, _, _, weight = calculate_rpe_set_values(
                table=table,
                intensity=intensity,
                effort=effort,
                volume=volume,
                max_weight=max_weight,
                rounding_step=rounding_step,
                rounding_mode=rounding_mode,
            )

            kwargs: dict[str, Any] = {
                "message": "RPE calculation completed successfully",
            }
            if weight is not None:
                kwargs["computed_weight"] = weight
                kwargs["suggested_weight"] = weight

            return rpe_pb2.RPEComputeResponse(**kwargs)

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
        try:
            while not context.cancelled():
                yield health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVING)
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass


async def serve(port: int = settings.GRPC_PORT) -> None:
    """Start gRPC server."""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    rpe_pb2_grpc.add_RPEServiceServicer_to_server(RPEServicer(), server)
    health_pb2_grpc.add_HealthServicer_to_server(HealthServicer(), server)

    server.add_insecure_port(f"[::]:{port}")
    logger.info("RPE gRPC server started on port %d", port)

    await server.start()
    try:
        await server.wait_for_termination()
    except asyncio.CancelledError:
        logger.info("RPE gRPC server stopping...")
        await server.stop(grace=5.0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    asyncio.run(serve())
