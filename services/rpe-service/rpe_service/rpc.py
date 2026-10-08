"""Inter-service RPC client for user-max-service."""

import logging

import httpx

from .config import settings

logger = logging.getLogger(__name__)


async def get_effective_max(user_max_id: int, user_id: str | None = None) -> float:
    """Fetch effective 1RM (verified_1rm -> true_1rm -> max_weight) from user-max-service."""
    base_url = settings.USER_MAX_SERVICE_URL.rstrip("/")
    headers = {"X-User-Id": user_id or "system"}

    # Support both direct microservice route (/user-max/id) and gateway route (/api/v1/user-max/id)
    candidate_urls = [
        f"{base_url}/user-max/{user_max_id}",
        f"{base_url}/api/v1/user-max/{user_max_id}",
    ]

    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=5.0) as client:
        for url in candidate_urls:
            try:
                response = await client.get(url, headers=headers)
                if response.status_code == 404 and url != candidate_urls[-1]:
                    continue
                response.raise_for_status()
                data = response.json()
                raw_max = data.get("verified_1rm") or data.get("true_1rm") or data.get("max_weight")
                if raw_max is None:
                    raise ValueError(f"No max weight found in response from {url}")
                return float(raw_max)
            except httpx.HTTPStatusError as e:
                last_error = RuntimeError(f"HTTP error {e.response.status_code} from {url}")
                logger.warning("Failed to fetch effective max from %s: %s", url, e)
            except httpx.RequestError as e:
                last_error = RuntimeError(f"Connection error to {url}: {e}")
                logger.warning("Connection error when fetching max from %s: %s", url, e)
            except Exception as e:
                last_error = e
                logger.warning("Unexpected error when fetching max from %s: %s", url, e)

    raise last_error or RuntimeError(f"Failed to fetch effective max for id {user_max_id}")

