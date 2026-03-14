from celery import Celery
from contracts import QueryRequest, TaskAcceptedResponse, TaskDetailResponse, TaskStatus
from core import get_settings
from fastapi import APIRouter, HTTPException, status

router = APIRouter(tags=["tasks"])
TASK_QUEUE = "celery"

settings = get_settings()
celery_client = Celery(
    "api-service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_client.conf.task_default_queue = TASK_QUEUE


def _map_celery_status(celery_status: str) -> TaskStatus:
    if celery_status in {"STARTED", "RETRY"}:
        return TaskStatus.in_progress
    if celery_status == "SUCCESS":
        return TaskStatus.completed
    if celery_status in {"FAILURE", "REVOKED"}:
        return TaskStatus.failed
    return TaskStatus.queued


@router.post(
    "/tasks/query", response_model=TaskAcceptedResponse, status_code=status.HTTP_202_ACCEPTED
)
def enqueue_query(payload: QueryRequest) -> TaskAcceptedResponse:
    try:
        async_result = celery_client.send_task(
            "celery_worker.llm_query",
            args=[payload.question, payload.model],
            queue=TASK_QUEUE,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to enqueue task") from exc

    return TaskAcceptedResponse(task_id=async_result.id, status=TaskStatus.queued)


@router.get("/tasks/query/{task_id}", response_model=TaskDetailResponse)
def get_query_task_status(task_id: str) -> TaskDetailResponse:
    async_result = celery_client.AsyncResult(task_id)
    task_status = _map_celery_status(async_result.status)

    result_payload: dict[str, object] | None = None
    error: str | None = None
    if task_status == TaskStatus.completed:
        result_payload = {"answer": async_result.result}
    if task_status == TaskStatus.failed:
        error = str(async_result.result)

    return TaskDetailResponse(
        task_id=task_id,
        status=task_status,
        result=result_payload,
        error=error,
    )
