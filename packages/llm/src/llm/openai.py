from dataclasses import dataclass
from typing import Any

from core.config import Settings, get_settings
from openai import OpenAI

DEFAULT_MODEL = "gpt-5.4-nano"


@dataclass(frozen=True, slots=True)
class TextGenerationRequest:
    system_prompt: str
    user_prompt: str
    model: str | None = None
    max_output_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class TextGenerationResult:
    text: str
    model: str


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

    resolved_client = client or OpenAI(api_key=api_key)
    response = resolved_client.responses.create(
        model=resolved_model,
        max_output_tokens=request.max_output_tokens,
        input=[
            {"role": "system", "content": cleaned_system_prompt},
            {"role": "user", "content": cleaned_user_prompt},
        ],
    )
    output_text = response.output_text.strip()
    if not output_text:
        raise RuntimeError("OpenAI returned an empty response")

    return TextGenerationResult(text=output_text, model=resolved_model)
