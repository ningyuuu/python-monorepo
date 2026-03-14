from celery import Celery
from contracts import (
    AddNumbersRequest,
    TaskAcceptedResponse,
    TaskDetailResponse,
    TaskIdsResponse,
    TaskStatus,
)
from core import get_settings
from fastapi import APIRouter, HTTPException, status
from tasks_db import (
    TaskNotFoundError,
    create_task,
    get_task,
    list_task_ids,
    mark_task_failed,
)

router = APIRouter(tags=["tasks"])
TASK_QUEUE = "celery"

settings = get_settings()
celery_client = Celery(
    "api-service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_client.conf.task_default_queue = TASK_QUEUE


@router.post(
    "/tasks/add", response_model=TaskAcceptedResponse, status_code=status.HTTP_202_ACCEPTED
)
def enqueue_add(payload: AddNumbersRequest) -> TaskAcceptedResponse:
    task_record = create_task(task_name="add_numbers", payload={"a": payload.a, "b": payload.b})

    try:
        celery_client.send_task(
            "celery_worker.add_numbers",
            args=[task_record.id],
            queue=TASK_QUEUE,
        )
    except Exception as exc:
        mark_task_failed(task_record.id, f"Failed to dispatch task: {exc}")
        raise HTTPException(status_code=503, detail="Unable to enqueue task") from exc

    return TaskAcceptedResponse(task_id=task_record.id, status=TaskStatus.queued)


@router.get("/tasks/add", response_model=TaskIdsResponse)
def get_task_ids() -> TaskIdsResponse:
    return TaskIdsResponse(task_ids=list_task_ids())


@router.get("/tasks/add/{task_id}", response_model=TaskDetailResponse)
def get_task_status(task_id: str) -> TaskDetailResponse:
    try:
        task = get_task(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc

    return TaskDetailResponse(
        task_id=task.id,
        status=TaskStatus(task.status),
        result=task.result,
        error=task.error,
    )
