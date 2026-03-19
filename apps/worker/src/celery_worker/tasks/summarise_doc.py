import logging
from io import BytesIO

from blob.vercel import get_bytes
from pypdf import PdfReader
from tasks_db import get_task, mark_task_completed, mark_task_failed, mark_task_in_progress

from celery_worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def _extract_text(blob_link: str, data: bytes) -> str:
    is_pdf = blob_link.lower().endswith(".pdf") or data.startswith(b"%PDF-")
    if is_pdf:
        reader = PdfReader(BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()

    return data.decode("utf-8", errors="replace")


@celery_app.task(name="celery_worker.summarise_doc")
def summarise_doc_task(task_id: str) -> str:
    resolved_task_id = str(task_id)
    task = get_task(resolved_task_id)
    mark_task_in_progress(resolved_task_id)

    try:
        blob_link = str(task.payload["blob_link"])
        blob_type = str(task.payload["blob_type"])

        if blob_type != "vercel":
            raise ValueError(f"unsupported blob type: {blob_type}")

        data = get_bytes(blob_link)

        text = _extract_text(blob_link, data)
        mark_task_completed(resolved_task_id, {"text": text})
        return text[:100] + "..." if len(text) > 100 else text
    except Exception as exc:
        mark_task_failed(resolved_task_id, str(exc))
        raise
