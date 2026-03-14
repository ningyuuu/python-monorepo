import logging

from core.config import get_settings
from openai import OpenAI

from celery_worker.celery_app import celery_app

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-5-nano"


@celery_app.task(name="celery_worker.llm_query")
def llm_query_task(question: str, model: str | None = None) -> str:
    cleaned_question = question.strip()
    if not cleaned_question:
        raise ValueError("question must not be empty")

    settings = get_settings()
    api_key = (settings.openai_api_key or "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set. Add it to your environment or .env file.")

    resolved_model = model or settings.openai_model or DEFAULT_MODEL
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

    logger.info(
        "Processed llm_query task",
        extra={"model": resolved_model},
    )
    return answer
