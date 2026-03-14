import pytest
from celery_worker.tasks import add_numbers_task
from celery_worker.tasks import llm_query as llm_query_module
from core.config import get_settings


def test_add_numbers_task() -> None:
    assert add_numbers_task(2, 3) == 5


def test_llm_query_task_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
    monkeypatch.setattr(
        llm_query_module,
        "get_task",
        lambda _task_id: type("Task", (), {"payload": {"question": "What is 2+2?"}})(),
    )
    monkeypatch.setattr(llm_query_module, "mark_task_in_progress", lambda _task_id: None)
    monkeypatch.setattr(llm_query_module, "mark_task_failed", lambda _task_id, _error: None)

    with pytest.raises(ValueError, match="OPENAI_API_KEY is not set"):
        llm_query_module.llm_query_task("task-123")
