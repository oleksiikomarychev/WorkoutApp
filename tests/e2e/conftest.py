import os

import httpx
import pytest


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.getenv("GATEWAY_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def internal_secret_headers() -> dict[str, str]:
    """Headers to bypass Firebase auth via INTERNAL_GATEWAY_SECRET.

    In CI this secret is provided via INTERNAL_GATEWAY_SECRET env var in the e2e job.
    """

    secret = os.getenv("INTERNAL_GATEWAY_SECRET", "test-secret")

    return {"X-Internal-Secret": secret, "X-User-Id": "e2e-user"}


@pytest.fixture
async def http_client() -> httpx.AsyncClient:
    async with httpx.AsyncClient(timeout=10.0) as client:
        yield client
