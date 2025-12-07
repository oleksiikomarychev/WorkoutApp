"""
Service HTTP client with safe JSON parsing and structured logging.

Usage:
    async with ServiceClient() as client:
        data = await client.get_json(url, headers=headers, default=[])
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeVar

import httpx
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


@dataclass
class ServiceResponse:
    """Result of a service call with parsed JSON or error info."""

    success: bool
    data: Any = None
    status_code: int | None = None
    error: str | None = None
    headers: dict[str, str] = field(default_factory=dict)

    def json_or(self, default: T) -> T | Any:
        """Return parsed data or default if request failed."""
        return self.data if self.success and self.data is not None else default


class ServiceClient:
    """
    Async HTTP client wrapper with:
    - Safe JSON parsing (no more try/except ValueError scattered everywhere)
    - Structured logging on errors
    - Configurable timeouts
    """

    def __init__(
        self,
        timeout: float | httpx.Timeout = 20.0,
        follow_redirects: bool = True,
    ) -> None:
        if isinstance(timeout, int | float):
            self._timeout = httpx.Timeout(timeout)
        else:
            self._timeout = timeout
        self._follow_redirects = follow_redirects
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> ServiceClient:
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=self._follow_redirects,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _parse_json(self, response: httpx.Response, url: str, **log_context: Any) -> Any | None:
        """Parse JSON from response, log and return None on failure."""
        try:
            return response.json()
        except ValueError:
            logger.error(
                "json_parse_failed",
                url=url,
                status_code=response.status_code,
                body_preview=response.text[:500] if response.text else "",
                **log_context,
            )
            return None

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        expected_status: int | tuple[int, ...] = 200,
        **log_context: Any,
    ) -> ServiceResponse:
        """Perform GET request and parse JSON response."""
        if isinstance(expected_status, int):
            expected_status = (expected_status,)

        try:
            assert self._client is not None, "Client not initialized"
            response = await self._client.get(url, headers=headers, params=params)
        except httpx.HTTPError as exc:
            logger.error("http_request_failed", url=url, error=str(exc), **log_context)
            return ServiceResponse(success=False, error=str(exc))

        if response.status_code not in expected_status:
            logger.error(
                "unexpected_status_code",
                url=url,
                status_code=response.status_code,
                expected=expected_status,
                body_preview=response.text[:500] if response.text else "",
                **log_context,
            )
            return ServiceResponse(
                success=False,
                status_code=response.status_code,
                error=f"Unexpected status {response.status_code}",
            )

        data = self._parse_json(response, url, **log_context)
        if data is None:
            return ServiceResponse(success=False, status_code=response.status_code, error="JSON parse failed")

        return ServiceResponse(
            success=True,
            data=data,
            status_code=response.status_code,
            headers=dict(response.headers),
        )

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: Any = None,
        content: bytes | str | None = None,
        expected_status: int | tuple[int, ...] = (200, 201),
        **log_context: Any,
    ) -> ServiceResponse:
        """Perform POST request and parse JSON response."""
        if isinstance(expected_status, int):
            expected_status = (expected_status,)

        try:
            assert self._client is not None
            response = await self._client.post(url, headers=headers, json=json, content=content)
        except httpx.HTTPError as exc:
            logger.error("http_request_failed", url=url, error=str(exc), **log_context)
            return ServiceResponse(success=False, error=str(exc))

        if response.status_code not in expected_status:
            logger.error(
                "unexpected_status_code",
                url=url,
                status_code=response.status_code,
                expected=expected_status,
                body_preview=response.text[:500] if response.text else "",
                **log_context,
            )
            return ServiceResponse(success=False, status_code=response.status_code)

        data = self._parse_json(response, url, **log_context)
        if data is None:
            return ServiceResponse(success=False, status_code=response.status_code, error="JSON parse failed")

        return ServiceResponse(
            success=True,
            data=data,
            status_code=response.status_code,
            headers=dict(response.headers),
        )

    async def get_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        default: T = None,  # type: ignore[assignment]
        expected_status: int | tuple[int, ...] = 200,
        **log_context: Any,
    ) -> T | Any:
        """GET + parse JSON, return default on any failure."""
        resp = await self.get(
            url,
            headers=headers,
            params=params,
            expected_status=expected_status,
            **log_context,
        )
        return resp.data if resp.success else default
