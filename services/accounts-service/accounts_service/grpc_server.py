"""gRPC server for accounts-service."""

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
    import workoutapp.common.common_pb2 as common_pb2  # noqa: F401
except ImportError:
    try:
        import common_pb2 as common_pb2  # noqa: F401
    except ImportError:
        pass

try:
    import workoutapp.accounts.accounts_pb2 as accounts_pb2
    import workoutapp.accounts.accounts_pb2_grpc as accounts_pb2_grpc
except ImportError:
    import accounts_pb2 as accounts_pb2  # type: ignore[no-redef]
    import accounts_pb2_grpc as accounts_pb2_grpc  # type: ignore[no-redef]

from .config import settings  # noqa: E402
from .database import get_db  # noqa: E402
from .models import UserAvatar  # noqa: E402
from .services.profile_service import ProfileData, ensure_profile_and_settings  # noqa: E402

logger = logging.getLogger("accounts_service.grpc")


def _proto_profile(profile_data: ProfileData | None) -> accounts_pb2.Profile | None:
    """Convert ProfileData object to proto Profile message."""
    if not profile_data:
        return None

    profile = profile_data.profile

    preferences: dict[str, str] = {}
    if profile_data.settings:
        preferences["unit_system"] = profile_data.settings.unit_system.value
        preferences["locale"] = profile_data.settings.locale
        if profile_data.settings.timezone:
            preferences["timezone"] = profile_data.settings.timezone

    return accounts_pb2.Profile(
        user_id=profile.user_id,
        email=profile.user_id,  # Identifier for identity context
        name=profile.display_name or "",
        photo_url=profile.photo_url or "",
        preferences=preferences,
    )


class AccountsServicer(accounts_pb2_grpc.AccountsServiceServicer):
    """gRPC servicer for Accounts service."""

    async def GetProfile(
        self,
        request: Any,
        context: grpc.aio.ServicerContext,
    ) -> accounts_pb2.GetProfileResponse:
        """Get user profile via gRPC."""
        user_id = request.user_context.user_id if request.user_context else None
        if not user_id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("user_id in user_context is required")
            return accounts_pb2.GetProfileResponse()

        try:
            async for db in get_db():
                data = await ensure_profile_and_settings(db, user_id)
                proto_profile = _proto_profile(data)
                return accounts_pb2.GetProfileResponse(profile=proto_profile)
        except Exception as e:
            logger.error("Failed to get profile for user %s: %s", user_id, str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return accounts_pb2.GetProfileResponse()

    async def UpdateProfile(
        self,
        request: Any,
        context: grpc.aio.ServicerContext,
    ) -> accounts_pb2.UpdateProfileResponse:
        """Update user profile via gRPC."""
        user_id = request.user_context.user_id if request.user_context else None
        if not user_id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("user_id in user_context is required")
            return accounts_pb2.UpdateProfileResponse()

        try:
            async for db in get_db():
                data = await ensure_profile_and_settings(db, user_id)
                profile = data.profile
                modified = False

                if request.profile and request.profile.name:
                    profile.display_name = request.profile.name
                    modified = True
                if request.profile and request.profile.photo_url:
                    profile.photo_url = request.profile.photo_url
                    modified = True

                if modified:
                    await db.commit()
                    await db.refresh(profile)

                proto_profile = _proto_profile(data)
                return accounts_pb2.UpdateProfileResponse(profile=proto_profile)
        except Exception as e:
            logger.error("Failed to update profile for user %s: %s", user_id, str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return accounts_pb2.UpdateProfileResponse()

    async def UploadAvatar(
        self,
        request: Any,
        context: grpc.aio.ServicerContext,
    ) -> accounts_pb2.UploadAvatarResponse:
        """Upload user avatar via gRPC."""
        user_id = request.user_context.user_id if request.user_context else None
        if not user_id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("user_id in user_context is required")
            return accounts_pb2.UploadAvatarResponse()

        try:
            async for db in get_db():
                result = await db.execute(select(UserAvatar).where(UserAvatar.user_id == user_id))
                avatar = result.scalar_one_or_none()

                if avatar:
                    avatar.image = request.image_data
                    avatar.content_type = request.content_type or "image/png"
                else:
                    avatar = UserAvatar(
                        user_id=user_id,
                        image=request.image_data,
                        content_type=request.content_type or "image/png",
                    )
                    db.add(avatar)

                await db.commit()

                photo_url = f"/accounts/{user_id}/avatar"
                return accounts_pb2.UploadAvatarResponse(photo_url=photo_url)
        except Exception as e:
            logger.error("Failed to upload avatar for user %s: %s", user_id, str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return accounts_pb2.UploadAvatarResponse()


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


async def serve(port: int = settings.ACCOUNTS_GRPC_PORT) -> None:
    """Start gRPC server."""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    accounts_pb2_grpc.add_AccountsServiceServicer_to_server(AccountsServicer(), server)
    health_pb2_grpc.add_HealthServicer_to_server(HealthServicer(), server)

    server.add_insecure_port(f"[::]:{port}")
    logger.info("Accounts gRPC server started on port %d", port)

    await server.start()
    try:
        await server.wait_for_termination()
    except asyncio.CancelledError:
        logger.info("Accounts gRPC server stopping...")
        await server.stop(grace=5.0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    asyncio.run(serve())
