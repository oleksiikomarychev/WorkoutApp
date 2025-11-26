from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel


class TaskSubmissionResponse(BaseModel):
    task_id: str
    status: str = "PENDING"


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
