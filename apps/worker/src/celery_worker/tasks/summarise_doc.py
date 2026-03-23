import logging
from io import BytesIO

from blob.vercel import get_bytes
from llm import TextGenerationRequest, generate_text
from pypdf import PdfReader
from tasks_db import get_task, mark_task_completed, mark_task_failed, mark_task_in_progress

from celery_worker.celery_app import celery_app

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = (
    "You are a concise document summarisation assistant. Summarise the provided document "
    "clearly and accurately. Focus on the main points, key facts, decisions, and action "
    "items. Do not invent details that are not present in the source text."
)
SUMMARY_MAX_OUTPUT_TOKENS = 4096


def _extract_text(blob_link: str, data: bytes) -> str:
    is_pdf = blob_link.lower().endswith(".pdf") or data.startswith(b"%PDF-")
    if is_pdf:
        reader = PdfReader(BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()

    return data.decode("utf-8", errors="replace")


def _summarise_text(text: str) -> str:
    cleaned_text = text.strip()
    if not cleaned_text:
        raise ValueError("text must not be empty")

    result = generate_text(
        TextGenerationRequest(
            system_prompt=SUMMARY_SYSTEM_PROMPT,
            user_prompt=f"Summarise the following document:\n\n{cleaned_text}",
            max_output_tokens=SUMMARY_MAX_OUTPUT_TOKENS,
        )
    )
    return result.text


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
        if not text.strip():
            raise ValueError("extracted text is empty")

        summary = _summarise_text(text)
        if not summary:
            raise ValueError("summary is empty")

        mark_task_completed(
            resolved_task_id,
            {"result": summary},
        )
        logger.info(
            "Processed summarise_doc task",
            extra={"task_id": resolved_task_id},
        )
        return summary[:100] + "..." if len(summary) > 100 else summary
    except Exception as exc:
        mark_task_failed(resolved_task_id, str(exc))
        raise
