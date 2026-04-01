import json
import logging
from io import BytesIO
from typing import Any

from blob.vercel import get_bytes
from celery import chord
from llm import TextGenerationRequest, generate_text
from pydantic import BaseModel, ConfigDict
from pypdf import PdfReader
from tasks_db import get_task, mark_task_completed, mark_task_failed, mark_task_in_progress

from celery_worker.celery_app import celery_app

logger = logging.getLogger(__name__)

EXTRACT_PO_ITEMS_SYSTEM_PROMPT = """You are a processor of raw PDF purchase order and pricing document text.

Follow the user's task exactly and return only the requested result.
Prefer concise, structured outputs that preserve the source meaning.
"""

EXTRACT_PO_ITEMS_RULES = (
    "Rules:\n"
    "- Return only individual purchase order line items; do not return subtotals.\n"
    "- Return all items found in the provided text chunk, not just a few examples.\n"
    "- Return item name, unit cost, quantity, unit type, and remarks with useful context.\n"
    "- If there are child items, return the child items instead of subtotal rows.\n"
    "- Exclude subtotals, totals, GST, remarks-only rows, headings, and aggregates.\n"
    "- Return JSON only.\n\n"
)

EXTRACT_CHUNK_SIZE_CHARS = 10_000
EXTRACT_MAX_OUTPUT_TOKENS = 20_000


class PurchaseOrderItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = ""
    unit_cost: float | None = 0.0
    qty_count: float | None = 0.0
    unit_type: str | None = ""
    remarks: str | None = ""


class PurchaseOrderItems(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[PurchaseOrderItem]


def _extract_text(blob_link: str, data: bytes) -> str:
    is_pdf = blob_link.lower().endswith(".pdf") or data.startswith(b"%PDF-")
    if is_pdf:
        reader = PdfReader(BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()

    return data.decode("utf-8", errors="replace")


def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1]).strip()
    return cleaned


def _split_document_into_chunks(
    document_text: str,
    chunk_chars: int = EXTRACT_CHUNK_SIZE_CHARS,
) -> list[str]:
    chunks: list[str] = []
    current_lines: list[str] = []
    current_length = 0

    for line in document_text.splitlines():
        line_with_newline = f"{line}\n"
        line_length = len(line_with_newline)

        if current_lines and current_length + line_length > chunk_chars:
            chunks.append("".join(current_lines).strip())
            current_lines = []
            current_length = 0

        current_lines.append(line_with_newline)
        current_length += line_length

    if current_lines:
        chunks.append("".join(current_lines).strip())

    return [chunk for chunk in chunks if chunk]


def _extract_po_items(document_text: str) -> PurchaseOrderItems:
    cleaned_text = document_text.strip()
    if not cleaned_text:
        raise ValueError("document_text must not be empty")

    schema_json = json.dumps(PurchaseOrderItems.model_json_schema(), ensure_ascii=False, indent=2)
    task_prompt = (
        "Task: Extract purchase order line items from the document text above.\n\n"
        f"{EXTRACT_PO_ITEMS_RULES}"
        f"JSON schema:\n{schema_json}"
    )

    result = generate_text(
        TextGenerationRequest(
            system_prompt=EXTRACT_PO_ITEMS_SYSTEM_PROMPT,
            user_prompt=(f"Document text:\n\n{cleaned_text}\n\n{task_prompt}"),
            max_output_tokens=EXTRACT_MAX_OUTPUT_TOKENS,
            reasoning_effort=None,
            text_verbosity=None,
        )
    )

    return PurchaseOrderItems.model_validate_json(_strip_code_fences(result.text))


def _combine_purchase_order_items(chunk_results: list[list[dict[str, Any]]]) -> PurchaseOrderItems:
    combined_items: list[PurchaseOrderItem] = []
    seen: set[tuple[str, float, float, str, str]] = set()

    for chunk_items in chunk_results:
        for item_payload in chunk_items:
            item = PurchaseOrderItem.model_validate(item_payload)
            key = (
                (item.name or "").strip().lower(),
                float(item.unit_cost or 0.0),
                float(item.qty_count or 0.0),
                (item.unit_type or "").strip().lower(),
                (item.remarks or "").strip().lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            combined_items.append(item)

    return PurchaseOrderItems(items=combined_items)


@celery_app.task(name="celery_worker.extract_po_items_chunk")
def extract_po_items_chunk_task(chunk_text: str) -> list[dict[str, Any]]:
    chunk_items = _extract_po_items(chunk_text)
    return [item.model_dump() for item in chunk_items.items]


@celery_app.task(name="celery_worker.extract_po_items_finalize")
def extract_po_items_finalize_task(
    chunk_results: list[list[dict[str, Any]]],
    parent_task_id: str,
) -> dict[str, Any]:
    try:
        combined_items = _combine_purchase_order_items(chunk_results)
        serialized_items = [item.model_dump() for item in combined_items.items]
        mark_task_completed(parent_task_id, {"items": serialized_items})
        logger.info(
            "Processed extract_po_items task",
            extra={"task_id": parent_task_id, "items_count": len(serialized_items)},
        )
        return {"items_count": len(serialized_items)}
    except Exception as exc:
        mark_task_failed(parent_task_id, str(exc))
        raise


@celery_app.task(name="celery_worker.extract_po_items_error")
def extract_po_items_error_task(
    request: Any,
    exc: Exception,
    traceback: Any,
    parent_task_id: str,
) -> None:
    mark_task_failed(parent_task_id, f"Chunk extraction failed: {exc}")


@celery_app.task(name="celery_worker.extract_po_items")
def extract_po_items_task(task_id: str) -> str:
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

        chunks = _split_document_into_chunks(text, chunk_chars=EXTRACT_CHUNK_SIZE_CHARS)
        if not chunks:
            raise ValueError("document did not produce any chunks")

        if len(chunks) == 1:
            chunk_items = extract_po_items_chunk_task(chunks[0])
            extract_po_items_finalize_task([chunk_items], resolved_task_id)
            return "Processed 1 chunk"

        header = [
            celery_app.signature("celery_worker.extract_po_items_chunk", args=[chunk])
            for chunk in chunks
        ]
        callback_signature = celery_app.signature(
            "celery_worker.extract_po_items_finalize",
            args=[resolved_task_id],
        )
        callback_signature.link_error(
            celery_app.signature("celery_worker.extract_po_items_error", args=[resolved_task_id])
        )

        chord(header)(callback_signature)

        logger.info(
            "Dispatched extract_po_items chunk tasks",
            extra={"task_id": resolved_task_id, "chunks_count": len(chunks)},
        )
        return f"Dispatched {len(chunks)} chunks"
    except Exception as exc:
        mark_task_failed(resolved_task_id, str(exc))
        raise
