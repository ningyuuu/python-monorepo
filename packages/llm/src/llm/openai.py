import logging
from dataclasses import dataclass
from typing import Any, cast

from core.config import Settings, get_settings
from openai import OpenAI

DEFAULT_MODEL = "gpt-5.4-nano"
DEFAULT_REASONING_EFFORT = "low"
DEFAULT_TEXT_VERBOSITY = "low"

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TextGenerationRequest:
    system_prompt: str
    user_prompt: str
    model: str | None = None
    max_output_tokens: int | None = None
    reasoning_effort: str | None = None
    text_verbosity: str | None = None


@dataclass(frozen=True, slots=True)
class TextGenerationResult:
    text: str
    model: str


def _get_value(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _extract_output_text(response: Any) -> str:
    direct_output_text = _get_value(response, "output_text")
    if isinstance(direct_output_text, str):
        cleaned_output_text = direct_output_text.strip()
        if cleaned_output_text:
            return cleaned_output_text

    output_items = _get_value(response, "output")
    if isinstance(output_items, list):
        collected_text: list[str] = []
        for output_item in output_items:
            content_items = _get_value(output_item, "content")
            if not isinstance(content_items, list):
                continue

            for content_item in content_items:
                content_type = _get_value(content_item, "type")
                if content_type not in {None, "output_text", "text"}:
                    continue

                text_value = _get_value(content_item, "text")
                if isinstance(text_value, str) and text_value.strip():
                    collected_text.append(text_value.strip())

        if collected_text:
            return "\n".join(collected_text)

    status = _get_value(response, "status")
    incomplete_details = _get_value(response, "incomplete_details")
    if incomplete_details:
        reason = _get_value(incomplete_details, "reason")
        if isinstance(reason, str) and reason:
            raise RuntimeError(f"OpenAI returned no text output (reason: {reason})")

    if isinstance(status, str) and status:
        raise RuntimeError(f"OpenAI returned no text output (status: {status})")

    raise RuntimeError("OpenAI returned an empty response")


def generate_text(
    request: TextGenerationRequest,
    *,
    settings: Settings | None = None,
    client: Any | None = None,
) -> TextGenerationResult:
    cleaned_system_prompt = request.system_prompt.strip()
    if not cleaned_system_prompt:
        raise ValueError("system_prompt must not be empty")

    cleaned_user_prompt = request.user_prompt.strip()
    if not cleaned_user_prompt:
        raise ValueError("user_prompt must not be empty")

    if request.max_output_tokens is not None and request.max_output_tokens <= 0:
        raise ValueError("max_output_tokens must be greater than 0")

    resolved_settings = settings or get_settings()
    api_key = (resolved_settings.openai_api_key or "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set. Add it to your environment or .env file.")

    resolved_model = (request.model or resolved_settings.openai_model or DEFAULT_MODEL).strip()
    if not resolved_model:
        resolved_model = DEFAULT_MODEL

    resolved_reasoning_effort = (
        (request.reasoning_effort or DEFAULT_REASONING_EFFORT).strip().lower()
    )
    if resolved_reasoning_effort not in {"low", "medium", "high"}:
        raise ValueError("reasoning_effort must be one of: low, medium, high")

    resolved_text_verbosity = (request.text_verbosity or DEFAULT_TEXT_VERBOSITY).strip().lower()
    if resolved_text_verbosity not in {"low", "medium", "high"}:
        raise ValueError("text_verbosity must be one of: low, medium, high")

    resolved_client = client or OpenAI(api_key=api_key)
    response = resolved_client.responses.create(
        model=resolved_model,
        max_output_tokens=request.max_output_tokens,
        reasoning=cast(Any, {"effort": resolved_reasoning_effort}),
        text=cast(Any, {"verbosity": resolved_text_verbosity}),
        input=[
            {"role": "system", "content": cleaned_system_prompt},
            {"role": "user", "content": cleaned_user_prompt},
        ],
    )

    logger.info(response)

    output_text = _extract_output_text(response)

    return TextGenerationResult(text=output_text, model=resolved_model)
