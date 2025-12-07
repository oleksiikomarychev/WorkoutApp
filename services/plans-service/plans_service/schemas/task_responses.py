from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class TaskSubmissionResponse(BaseModel):
    task_id: str
    status: str = "PENDING"


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Any | None = None
    error: str | None = None
    meta: dict[str, Any] | None = None
