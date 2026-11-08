"""Inter-service RPC client for user-max-service."""

import asyncio
import logging
import math

import httpx

from .config import settings

logger = logging.getLogger(__name__)

_DEFAULT_CLIENT: httpx.AsyncClient | None = None
_CLIENT_LOOP: asyncio.AbstractEventLoop | None = None


def get_http_client() -> httpx.AsyncClient:
    """Get or initialize a loop-bound reusable HTTP client."""
    global _DEFAULT_CLIENT, _CLIENT_LOOP
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _DEFAULT_CLIENT is None or _DEFAULT_CLIENT.is_closed or _CLIENT_LOOP != current_loop:
        _CLIENT_LOOP = current_loop
        _DEFAULT_CLIENT = httpx.AsyncClient(
            timeout=5.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )
    return _DEFAULT_CLIENT


async def close_http_client() -> None:
    """Gracefully close the global HTTP client if open."""
    global _DEFAULT_CLIENT, _CLIENT_LOOP
    if _DEFAULT_CLIENT is not None and not _DEFAULT_CLIENT.is_closed:
        await _DEFAULT_CLIENT.aclose()
    _DEFAULT_CLIENT = None
    _CLIENT_LOOP = None


async def get_effective_max(
    user_max_id: int,
    user_id: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> float:
    """Fetch effective 1RM (verified_1rm -> true_1rm -> max_weight) from user-max-service."""
    base_url = settings.USER_MAX_SERVICE_URL.rstrip("/")
    headers = {
        "X-User-Id": user_id or "system",
    }
    if settings.INTERNAL_GATEWAY_SECRET:
        headers["X-Internal-Secret"] = settings.INTERNAL_GATEWAY_SECRET

    # Support both direct microservice route (/user-max/id) and gateway route (/api/v1/user-max/id)
    candidate_urls = [
        f"{base_url}/user-max/{user_max_id}",
        f"{base_url}/api/v1/user-max/{user_max_id}",
    ]

    async def _execute_fetch(http_client: httpx.AsyncClient) -> float:
        last_error: Exception | None = None
        for url in candidate_urls:
            try:
                response = await http_client.get(url, headers=headers)
                if response.status_code == 404 and url != candidate_urls[-1]:
                    continue
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError(f"Expected dict response from {url}, got {type(data).__name__}")

                # Prioritize verified_1rm -> true_1rm -> max_weight with strict positive finite check
                for field in ("verified_1rm", "true_1rm", "max_weight"):
                    val = data.get(field)
                    if val is not None:
                        try:
                            parsed = float(val)
                            if math.isfinite(parsed) and parsed > 0:
                                return parsed
                        except (ValueError, TypeError):
                            continue

                raise ValueError(f"No valid max weight found in response from {url}: {data}")
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

    if client is not None:
        return await _execute_fetch(client)

    return await _execute_fetch(get_http_client())
