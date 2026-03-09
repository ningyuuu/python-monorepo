from celery import Celery
from contracts import AddNumbersRequest, TaskAcceptedResponse, TaskStatus
from core import get_settings
from fastapi import APIRouter, HTTPException, status
from tasks_db import create_task, mark_task_failed

router = APIRouter(tags=["tasks"])

settings = get_settings()
celery_client = Celery(
    "api-service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)


@router.post("/add", response_model=TaskAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
def enqueue_add(payload: AddNumbersRequest) -> TaskAcceptedResponse:
    task_record = create_task(task_name="add_numbers", payload={"a": payload.a, "b": payload.b})

    try:
        celery_client.send_task("celery_worker.add_numbers", args=[task_record.id])
    except Exception as exc:
        mark_task_failed(task_record.id, f"Failed to dispatch task: {exc}")
        raise HTTPException(status_code=503, detail="Unable to enqueue task") from exc

    return TaskAcceptedResponse(task_id=task_record.id, status=TaskStatus.queued)
