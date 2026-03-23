from core.config import Settings
from llm import TextGenerationRequest, TextGenerationResult, generate_text


class _FakeResponsesClient:
    def __init__(self, output_text: str, *, output: list[object] | None = None) -> None:
        self.output_text = output_text
        self.output = output
        self.calls: list[dict[str, object]] = []

    def create(
        self,
        *,
        model: str,
        input: list[dict[str, str]],
        max_output_tokens: int | None = None,
        reasoning: dict[str, str] | None = None,
        text: dict[str, str] | None = None,
    ) -> object:
        self.calls.append(
            {
                "model": model,
                "input": input,
                "max_output_tokens": max_output_tokens,
                "reasoning": reasoning,
                "text": text,
            }
        )
        return type(
            "Response",
            (),
            {"output_text": self.output_text, "output": self.output, "status": "completed"},
        )()


class _FakeOpenAIClient:
    def __init__(self, output_text: str, *, output: list[object] | None = None) -> None:
        self.responses = _FakeResponsesClient(output_text, output=output)


def test_generate_text_calls_openai_responses_api() -> None:
    client = _FakeOpenAIClient("  4  ")
    result = generate_text(
        TextGenerationRequest(
            system_prompt=" You are concise. ",
            user_prompt=" What is 2+2? ",
            model="gpt-test",
            max_output_tokens=32,
        ),
        settings=Settings(openai_api_key="test-key", openai_model="gpt-default"),
        client=client,
    )

    assert result == TextGenerationResult(text="4", model="gpt-test")
    assert client.responses.calls == [
        {
            "model": "gpt-test",
            "max_output_tokens": 32,
            "reasoning": {"effort": "low"},
            "text": {"verbosity": "low"},
            "input": [
                {"role": "system", "content": "You are concise."},
                {"role": "user", "content": "What is 2+2?"},
            ],
        }
    ]


def test_generate_text_requires_api_key() -> None:
    try:
        generate_text(
            TextGenerationRequest(system_prompt="You are concise.", user_prompt="Hello"),
            settings=Settings(openai_api_key=None, openai_model="gpt-default"),
        )
    except ValueError as exc:
        assert "OPENAI_API_KEY is not set" in str(exc)
    else:
        raise AssertionError("Expected generate_text to require an API key")


def test_generate_text_rejects_blank_user_prompt() -> None:
    try:
        generate_text(
            TextGenerationRequest(system_prompt="You are concise.", user_prompt="   "),
            settings=Settings(openai_api_key="test-key", openai_model="gpt-default"),
            client=_FakeOpenAIClient("unused"),
        )
    except ValueError as exc:
        assert str(exc) == "user_prompt must not be empty"
    else:
        raise AssertionError("Expected generate_text to reject a blank user prompt")


def test_generate_text_rejects_non_positive_output_token_limit() -> None:
    try:
        generate_text(
            TextGenerationRequest(
                system_prompt="You are concise.",
                user_prompt="Hello",
                max_output_tokens=0,
            ),
            settings=Settings(openai_api_key="test-key", openai_model="gpt-default"),
            client=_FakeOpenAIClient("unused"),
        )
    except ValueError as exc:
        assert str(exc) == "max_output_tokens must be greater than 0"
    else:
        raise AssertionError("Expected generate_text to reject a non-positive output token limit")


def test_generate_text_falls_back_to_nested_output_content() -> None:
    client = _FakeOpenAIClient(
        "",
        output=[
            {
                "content": [
                    {"type": "output_text", "text": "Summary paragraph one."},
                    {"type": "output_text", "text": "Summary paragraph two."},
                ]
            }
        ],
    )

    result = generate_text(
        TextGenerationRequest(
            system_prompt="You are concise.",
            user_prompt="Summarise this text.",
        ),
        settings=Settings(openai_api_key="test-key", openai_model="gpt-default"),
        client=client,
    )

    assert result == TextGenerationResult(
        text="Summary paragraph one.\nSummary paragraph two.",
        model="gpt-default",
    )


def test_generate_text_includes_incomplete_reason_in_error() -> None:
    class _IncompleteResponsesClient(_FakeResponsesClient):
        def create(
            self,
            *,
            model: str,
            input: list[dict[str, str]],
            max_output_tokens: int | None = None,
            reasoning: dict[str, str] | None = None,
            text: dict[str, str] | None = None,
        ) -> object:
            self.calls.append(
                {
                    "model": model,
                    "input": input,
                    "max_output_tokens": max_output_tokens,
                    "reasoning": reasoning,
                    "text": text,
                }
            )
            return type(
                "Response",
                (),
                {
                    "output_text": "",
                    "output": [],
                    "status": "incomplete",
                    "incomplete_details": {"reason": "max_output_tokens"},
                },
            )()

    client = _FakeOpenAIClient("unused")
    client.responses = _IncompleteResponsesClient("unused")

    try:
        generate_text(
            TextGenerationRequest(
                system_prompt="You are concise.",
                user_prompt="Summarise this text.",
                max_output_tokens=1,
            ),
            settings=Settings(openai_api_key="test-key", openai_model="gpt-default"),
            client=client,
        )
    except RuntimeError as exc:
        assert str(exc) == "OpenAI returned no text output (reason: max_output_tokens)"
    else:
        raise AssertionError("Expected generate_text to surface the incomplete reason")


def test_generate_text_rejects_invalid_reasoning_effort() -> None:
    try:
        generate_text(
            TextGenerationRequest(
                system_prompt="You are concise.",
                user_prompt="Hello",
                reasoning_effort="minimal",
            ),
            settings=Settings(openai_api_key="test-key", openai_model="gpt-default"),
            client=_FakeOpenAIClient("unused"),
        )
    except ValueError as exc:
        assert str(exc) == "reasoning_effort must be one of: low, medium, high"
    else:
        raise AssertionError("Expected generate_text to reject an invalid reasoning_effort")
