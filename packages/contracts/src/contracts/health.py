from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class TaskStatus(StrEnum):
    queued = "queued"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class HealthResponse(BaseModel):
    status: str
    service: str
    message: str


class AddNumbersRequest(BaseModel):
    a: int
    b: int


class TaskAcceptedResponse(BaseModel):
    task_id: str
    status: TaskStatus


class TaskDetailResponse(BaseModel):
    task_id: str
    status: TaskStatus
    result: dict[str, Any] | None
    error: str | None


class TaskIdsResponse(BaseModel):
    task_ids: list[str]
