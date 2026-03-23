import logging

from llm import TextGenerationRequest, generate_text
from tasks_db import get_task, mark_task_completed, mark_task_failed, mark_task_in_progress

from celery_worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="celery_worker.llm_query")
def llm_query_task(task_id: str) -> str:
    resolved_task_id = str(task_id)
    task = get_task(resolved_task_id)
    mark_task_in_progress(resolved_task_id)

    try:
        cleaned_question = str(task.payload["question"]).strip()
        if not cleaned_question:
            raise ValueError("question must not be empty")

        result = generate_text(
            TextGenerationRequest(
                system_prompt="You are a concise, helpful Q&A assistant.",
                user_prompt=cleaned_question,
                max_output_tokens=1024,
            )
        )

        mark_task_completed(
            resolved_task_id,
            {
                "answer": result.text,
                "model": result.model,
            },
        )
        logger.info(
            "Processed llm_query task",
            extra={"task_id": resolved_task_id, "model": result.model},
        )
        return result.text
    except Exception as exc:
        mark_task_failed(resolved_task_id, str(exc))
        raise
