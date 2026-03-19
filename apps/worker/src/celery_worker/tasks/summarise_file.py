import logging

import vercel_blob
from core.config import get_settings
from tasks_db import get_task, mark_task_completed, mark_task_failed, mark_task_in_progress

from celery_worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="celery_worker.summarise_file")
def summarise_file_task(task_id: str) -> str:
    resolved_task_id = str(task_id)
    task = get_task(resolved_task_id)
    mark_task_in_progress(resolved_task_id)

    try:
        blob_link = str(task.payload["blob_link"])
        blob_type = str(task.payload["blob_type"])

        if blob_type != "vercel":
            raise ValueError(f"unsupported blob type: {blob_type}")

        token = get_settings().blob_read_write_token
        options = {"token": token} if token else {}
        data: bytes | None = vercel_blob.download_file(blob_link, options=options)
        if data is None:
            raise RuntimeError(f"failed to download blob: {blob_link}")

        text = data.decode("utf-8")
        mark_task_completed(resolved_task_id, {"text": text})
        return text
    except Exception as exc:
        mark_task_failed(resolved_task_id, str(exc))
        raise
