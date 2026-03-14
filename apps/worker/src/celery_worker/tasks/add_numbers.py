import logging

from monorepo_domain import add_numbers
from tasks_db import (
    get_task,
    mark_task_completed,
    mark_task_failed,
    mark_task_in_progress,
)

from celery_worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="celery_worker.add_numbers")
def add_numbers_task(task_id: str | int, b: int | None = None) -> int:
    if b is not None:
        return add_numbers(int(task_id), b)

    resolved_task_id = str(task_id)
    task = get_task(resolved_task_id)
    mark_task_in_progress(resolved_task_id)

    try:
        a = int(task.payload["a"])
        b = int(task.payload["b"])
        result = add_numbers(a, b)
        mark_task_completed(resolved_task_id, {"value": result})
        logger.info(
            "Processed add_numbers task",
            extra={
                "task_id": resolved_task_id,
                "a": a,
                "b": b,
                "result": result,
            },
        )
        return result
    except Exception as exc:
        mark_task_failed(resolved_task_id, str(exc))
        raise
