from enum import StrEnum

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
