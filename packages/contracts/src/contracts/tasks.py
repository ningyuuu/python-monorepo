from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class TaskStatus(StrEnum):
    queued = "queued"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


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


class TaskListItem(BaseModel):
    task_id: str
    email: str
    task_name: str
    status: TaskStatus
    created_at: datetime
    result: dict[str, Any] | None
    error: str | None


class TaskListResponse(BaseModel):
    tasks: list[TaskListItem]
