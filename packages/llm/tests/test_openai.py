from core.config import Settings
from llm import TextGenerationRequest, TextGenerationResult, generate_text


class _FakeResponsesClient:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.calls: list[dict[str, object]] = []

    def create(
        self,
        *,
        model: str,
        input: list[dict[str, str]],
        max_output_tokens: int | None = None,
    ) -> object:
        self.calls.append(
            {
                "model": model,
                "input": input,
                "max_output_tokens": max_output_tokens,
            }
        )
        return type("Response", (), {"output_text": self.output_text})()


class _FakeOpenAIClient:
    def __init__(self, output_text: str) -> None:
        self.responses = _FakeResponsesClient(output_text)


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
