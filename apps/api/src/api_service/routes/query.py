from contracts import QueryRequest, TaskAcceptedResponse, TaskDetailResponse, TaskStatus
from fastapi import APIRouter, HTTPException, status
from tasks_db import TaskNotFoundError, create_task, get_task, mark_task_failed

from api_service.celery_client import send_worker_task

router = APIRouter(tags=["tasks"])


@router.post(
    "/tasks/query", response_model=TaskAcceptedResponse, status_code=status.HTTP_202_ACCEPTED
)
def enqueue_query(payload: QueryRequest) -> TaskAcceptedResponse:
    task_record = create_task(
        task_name="llm_query",
        payload={"question": payload.question},
        email=str(payload.email),
    )

    try:
        send_worker_task("celery_worker.llm_query", task_record.id)
    except Exception as exc:
        mark_task_failed(task_record.id, f"Failed to dispatch task: {exc}")
        raise HTTPException(status_code=503, detail="Unable to enqueue task") from exc

    return TaskAcceptedResponse(task_id=task_record.id, status=TaskStatus.queued)


@router.get("/tasks/query/{task_id}", response_model=TaskDetailResponse)
def get_query_task_status(task_id: str) -> TaskDetailResponse:
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
