import asyncio
import logging
import sys
from concurrent import futures
from pathlib import Path

import grpc

# from grpc_health.v1 import health_pb2
# from grpc_health.v1 import health_pb2_grpc

# Add proto_gen to path for imports
proto_gen_path = Path(__file__).parent.parent / "proto_gen"
sys.path.insert(0, str(proto_gen_path))

import accounts_pb2 as accounts_pb2
import accounts_pb2_grpc as accounts_pb2_grpc

from .database import get_db
from .services.profile_service import ensure_profile_and_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _proto_profile(profile_data):
    """Convert profile data to proto Profile."""
    if not profile_data:
        return None
    
    profile = profile_data.profile
    
    return accounts_pb2.Profile(
        user_id=profile.user_id,
        email=profile.user_id,  # Using user_id as email for now
        name=profile.display_name,
        photo_url=profile.photo_url or "",
        preferences={},  # Could add settings as preferences
    )


class AccountsServicer(accounts_pb2_grpc.AccountsServiceServicer):
    """gRPC servicer for Accounts service."""

    async def GetProfile(self, request, context):
        """Get user profile."""
        try:
            user_id = request.user_context.user_id if request.user_context else None
            
            async for db in get_db():
                data = await ensure_profile_and_settings(db, user_id)
                proto_profile = _proto_profile(data)
                
                return accounts_pb2.GetProfileResponse(profile=proto_profile)
        except Exception as e:
            logger.error(f"Failed to get profile for user {user_id}: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return accounts_pb2.GetProfileResponse()

    async def UpdateProfile(self, request, context):
        """Update user profile."""
        try:
            user_id = request.user_context.user_id if request.user_context else None
            
            async for db in get_db():
                data = await ensure_profile_and_settings(db, user_id)
                profile = data.profile
                modified = False
                
                if request.profile.name:
                    profile.display_name = request.profile.name
                    modified = True
                if request.profile.photo_url:
                    profile.photo_url = request.profile.photo_url
                    modified = True
                
                if modified:
                    await db.commit()
                    await db.refresh(profile)
                
                proto_profile = _proto_profile(data)
                return accounts_pb2.UpdateProfileResponse(profile=proto_profile)
        except Exception as e:
            logger.error(f"Failed to update profile for user {user_id}: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return accounts_pb2.UpdateProfileResponse()

    async def UploadAvatar(self, request, context):
        """Upload user avatar."""
        try:
            user_id = request.user_context.user_id if request.user_context else None
            
            async for db in get_db():
                from sqlalchemy import select

                from ..models import UserAvatar
                
                # Check if avatar exists
                result = await db.execute(
                    select(UserAvatar).where(UserAvatar.user_id == user_id)
                )
                avatar = result.scalar_one_or_none()
                
                if avatar:
                    avatar.image = request.image_data
                    avatar.content_type = request.content_type
                else:
                    avatar = UserAvatar(
                        user_id=user_id,
                        image=request.image_data,
                        content_type=request.content_type,
                    )
                    db.add(avatar)
                
                await db.commit()
                
                # Return a placeholder URL
                photo_url = f"/accounts/{user_id}/avatar"
                return accounts_pb2.UploadAvatarResponse(photo_url=photo_url)
        except Exception as e:
            logger.error(f"Failed to upload avatar for user {user_id}: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return accounts_pb2.UploadAvatarResponse()


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


async def serve(port: int = 50055):
    """Start gRPC server."""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    accounts_pb2_grpc.add_AccountsServiceServicer_to_server(AccountsServicer(), server)
    # health_pb2_grpc.add_HealthServicer_to_server(HealthServicer(), server)

    server.add_insecure_port(f"[::]:{port}")
    logger.info(f"Accounts gRPC server started on port {port}")

    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
