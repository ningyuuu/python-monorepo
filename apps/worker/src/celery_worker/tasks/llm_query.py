import logging

from core.config import get_settings
from openai import OpenAI
from tasks_db import get_task, mark_task_completed, mark_task_failed, mark_task_in_progress

from celery_worker.celery_app import celery_app

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-5-nano"


@celery_app.task(name="celery_worker.llm_query")
def llm_query_task(task_id: str) -> str:
    resolved_task_id = str(task_id)
    task = get_task(resolved_task_id)
    mark_task_in_progress(resolved_task_id)

    try:
        cleaned_question = str(task.payload["question"]).strip()
        if not cleaned_question:
            raise ValueError("question must not be empty")

        settings = get_settings()
        api_key = (settings.openai_api_key or "").strip()
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set. Add it to your environment or .env file.")

        resolved_model = settings.openai_model or DEFAULT_MODEL
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=resolved_model,
            input=[
                {
                    "role": "system",
                    "content": "You are a concise, helpful Q&A assistant.",
                },
                {"role": "user", "content": cleaned_question},
            ],
        )
        answer = response.output_text.strip()
        if not answer:
            raise RuntimeError("OpenAI returned an empty response")

        mark_task_completed(
            resolved_task_id,
            {
                "answer": answer,
                "model": resolved_model,
            },
        )
        logger.info(
            "Processed llm_query task",
            extra={"task_id": resolved_task_id, "model": resolved_model},
        )
        return answer
    except Exception as exc:
        mark_task_failed(resolved_task_id, str(exc))
        raise
