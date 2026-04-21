from contracts import (
    ExtractPoItemsRequest,
    TaskAcceptedResponse,
    TaskDetailResponse,
    TaskListItem,
    TaskListResponse,
    TaskStatus,
)
from fastapi import APIRouter, HTTPException, status
from tasks_db import TaskNotFoundError, create_task, get_task, list_tasks, mark_task_failed

from api_service.celery_client import send_worker_task

router = APIRouter(tags=["tasks"])


@router.post(
    "/tasks/extract_po_items",
    response_model=TaskAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def enqueue_extract_po_items(payload: ExtractPoItemsRequest) -> TaskAcceptedResponse:
    task_record = create_task(
        task_name="extract_po_items",
        payload={
            "user_link": payload.user_link,
            "blob_link": payload.blob_link,
            "blob_type": payload.blob_type,
        },
        email=str(payload.email),
    )

    try:
        send_worker_task("celery_worker.extract_po_items", task_record.id)
    except Exception as exc:
        mark_task_failed(task_record.id, f"Failed to dispatch task: {exc}")
        raise HTTPException(status_code=503, detail="Unable to enqueue task") from exc

    return TaskAcceptedResponse(task_id=task_record.id, status=TaskStatus.queued)


@router.get("/tasks/extract_po_items/{task_id}", response_model=TaskDetailResponse)
def get_extract_po_items_task_status(task_id: str) -> TaskDetailResponse:
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


@router.get("/tasks/extract_po_items", response_model=TaskListResponse)
def list_extract_po_items_tasks(limit: int = 50) -> TaskListResponse:
    tasks = list_tasks(task_name="extract_po_items", limit=limit)
    return TaskListResponse(
        tasks=[
            TaskListItem(
                task_id=task.id,
                email=task.email,
                task_name=task.task_name,
                status=TaskStatus(task.status),
                created_at=task.created_at,
                result=task.result,
                error=task.error,
            )
            for task in tasks
        ]
    )
