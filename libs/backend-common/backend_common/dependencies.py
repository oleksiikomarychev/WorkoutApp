from collections.abc import AsyncGenerator, Callable, Generator

from fastapi import Header, HTTPException, Request, status
from sentry_sdk import set_tag, set_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session


def make_get_db_async(
    async_session_factory: Callable[[], AsyncSession],
) -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    async def get_db() -> AsyncGenerator[AsyncSession, None]:
        async with async_session_factory() as session:
            yield session

    return get_db


def make_get_db_sync(
    session_factory: Callable[[], Session],
) -> Callable[[], Generator[Session, None, None]]:
    def get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    return get_db


def make_get_current_user_id(
    service_name: str,
    header_name: str = "x-user-id",
    error_status_code: int = status.HTTP_401_UNAUTHORIZED,
    error_detail: str = "X-User-Id header required",
) -> Callable[[Request], str]:
    def get_current_user_id(request: Request) -> str:
        user_id = request.headers.get(header_name)
        if not user_id:
            raise HTTPException(status_code=error_status_code, detail=error_detail)
        set_user({"id": str(user_id)})
        set_tag("service", service_name)
        return user_id

    return get_current_user_id


def make_get_current_user_id_header(
    service_name: str,
    header_alias: str = "X-User-Id",
    error_status_code: int = status.HTTP_401_UNAUTHORIZED,
    error_detail: str = "X-User-Id header required",
) -> Callable[[str | None], str]:
    def get_current_user_id(x_user_id: str | None = Header(default=None, alias=header_alias)) -> str:  # type: ignore[assignment]
        if not x_user_id:
            raise HTTPException(status_code=error_status_code, detail=error_detail)
        set_user({"id": str(x_user_id)})
        set_tag("service", service_name)
        return x_user_id

    return get_current_user_id
