import pytest
from celery_worker.tasks import add_numbers_task
from celery_worker.tasks.llm_query import llm_query_task
from core.config import get_settings


def test_add_numbers_task() -> None:
    assert add_numbers_task(2, 3) == 5


def test_llm_query_task_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="OPENAI_API_KEY is not set"):
        llm_query_task("What is 2+2?")
