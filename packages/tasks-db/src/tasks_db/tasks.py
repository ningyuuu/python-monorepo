from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session, init_db
from .models import TaskRecord, TaskStatus


class TaskNotFoundError(Exception):
    pass


Payload = dict[str, Any]


def _get_task_record(session: Session, task_id: str) -> TaskRecord:
    task = session.get(TaskRecord, task_id)
    if task is None:
        raise TaskNotFoundError(f"Task {task_id} was not found")
    return task


def create_task(task_name: str, payload: Payload, email: str) -> TaskRecord:
    init_db()
    task = TaskRecord(
        id=str(uuid4()),
        email=email,
        task_name=task_name,
        payload=payload,
        status=TaskStatus.queued,
    )
    with get_session() as session:
        session.add(task)
        session.commit()
        session.refresh(task)
        return task


def get_task(task_id: str) -> TaskRecord:
    init_db()
    with get_session() as session:
        task = _get_task_record(session, task_id)
        session.expunge(task)
        return task


def list_task_ids() -> list[str]:
    init_db()
    with get_session() as session:
        statement = select(TaskRecord.id).order_by(TaskRecord.created_at.desc())
        return list(session.scalars(statement))


def list_tasks(task_name: str | None = None, limit: int = 50) -> list[TaskRecord]:
    init_db()
    with get_session() as session:
        statement = select(TaskRecord).order_by(TaskRecord.created_at.desc())
        if task_name:
            statement = statement.where(TaskRecord.task_name == task_name)
        statement = statement.limit(limit)
        tasks = list(session.scalars(statement))
        for task in tasks:
            session.expunge(task)
        return tasks


def mark_task_in_progress(task_id: str) -> TaskRecord:
    return _update_task(task_id=task_id, status=TaskStatus.in_progress, error=None)


def mark_task_completed(task_id: str, result: Payload) -> TaskRecord:
    return _update_task(
        task_id=task_id,
        status=TaskStatus.completed,
        result=result,
        error=None,
    )


def mark_task_failed(task_id: str, error: str) -> TaskRecord:
    return _update_task(task_id=task_id, status=TaskStatus.failed, error=error)


def _update_task(
    task_id: str,
    status: TaskStatus,
    result: Payload | None = None,
    error: str | None = None,
) -> TaskRecord:
    init_db()
    with get_session() as session:
        task = _get_task_record(session, task_id)
        task.status = status
        task.result = result
        task.error = error
        session.commit()
        session.refresh(task)
        session.expunge(task)
        return task
