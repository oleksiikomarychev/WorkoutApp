import logging
import sys
from pathlib import Path

import grpc
import grpc.aio

# Add proto_gen to path for imports
proto_gen_path = Path(__file__).parent.parent / "proto_gen"
sys.path.insert(0, str(proto_gen_path))

import accounts_pb2 as accounts_pb2
import accounts_pb2_grpc as accounts_pb2_grpc
import common_pb2 as common_pb2
import exercises_pb2 as exercises_pb2
import exercises_pb2_grpc as exercises_pb2_grpc
import plans_pb2 as plans_pb2
import plans_pb2_grpc as plans_pb2_grpc
import rpe_pb2 as rpe_pb2
import rpe_pb2_grpc as rpe_pb2_grpc
import workouts_pb2 as workouts_pb2
import workouts_pb2_grpc as workouts_pb2_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class GRPCClientManager:
    """Manages gRPC client connections to backend services."""
    
    def __init__(self):
        self._channels = {}
        self._stubs = {}
    
    async def get_channel(self, service_name: str, host: str, port: int) -> grpc.aio.Channel:
        """Get or create a gRPC channel for a service."""
        key = f"{service_name}:{host}:{port}"
        
        if key not in self._channels:
            channel = grpc.aio.insecure_channel(f"{host}:{port}")
            self._channels[key] = channel
            logger.info(f"Created gRPC channel for {service_name} at {host}:{port}")
        
        return self._channels[key]
    
    async def get_rpe_stub(self, host: str = "rpe-service", port: int = 50051) -> rpe_pb2_grpc.RPEServiceStub:
        """Get RPE service stub."""
        channel = await self.get_channel("rpe-service", host, port)
        return rpe_pb2_grpc.RPEServiceStub(channel)
    
    async def get_exercises_stub(self, host: str = "exercises-service", port: int = 50052) -> exercises_pb2_grpc.ExercisesServiceStub:
        """Get Exercises service stub."""
        channel = await self.get_channel("exercises-service", host, port)
        return exercises_pb2_grpc.ExercisesServiceStub(channel)
    
    async def get_plans_stub(self, host: str = "plans-service", port: int = 50053) -> plans_pb2_grpc.PlansServiceStub:
        """Get Plans service stub."""
        channel = await self.get_channel("plans-service", host, port)
        return plans_pb2_grpc.PlansServiceStub(channel)
    
    async def get_workouts_stub(self, host: str = "workouts-service", port: int = 50054) -> workouts_pb2_grpc.WorkoutServiceStub:
        """Get Workouts service stub."""
        channel = await self.get_channel("workouts-service", host, port)
        return workouts_pb2_grpc.WorkoutServiceStub(channel)
    
    async def get_accounts_stub(self, host: str = "accounts-service", port: int = 50055) -> accounts_pb2_grpc.AccountsServiceStub:
        """Get Accounts service stub."""
        channel = await self.get_channel("accounts-service", host, port)
        return accounts_pb2_grpc.AccountsServiceStub(channel)
    
    async def close_all(self):
        """Close all gRPC channels."""
        for key, channel in self._channels.items():
            await channel.close()
            logger.info(f"Closed gRPC channel for {key}")
        self._channels.clear()
        self._stubs.clear()


# Global client manager instance
grpc_client_manager = GRPCClientManager()


def headers_to_metadata(headers: dict[str, str]) -> list[tuple[str, str]]:
    """Convert HTTP headers to gRPC metadata."""
    metadata = []
    for key, value in headers.items():
        # Convert header names to lowercase for gRPC
        metadata.append((key.lower(), value))
    return metadata


def metadata_to_headers(metadata: list[tuple[str, str]]) -> dict[str, str]:
    """Convert gRPC metadata to HTTP headers."""
    headers = {}
    for key, value in metadata:
        headers[key] = value
    return headers


def create_user_context(user_id: str, email: str = "", name: str = "") -> common_pb2.UserContext:
    """Create a UserContext proto message."""
    return common_pb2.UserContext(
        user_id=user_id,
        email=email,
        name=name,
    )
