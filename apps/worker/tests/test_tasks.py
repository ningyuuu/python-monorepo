import pytest
from celery_worker.tasks import add_numbers_task
from celery_worker.tasks import llm_query as llm_query_module
from llm import TextGenerationResult


def test_add_numbers_task() -> None:
    assert add_numbers_task(2, 3) == 5


def test_llm_query_task_delegates_to_llm_package(monkeypatch: pytest.MonkeyPatch) -> None:
    completed_payload: dict[str, object] = {}

    monkeypatch.setattr(
        llm_query_module,
        "get_task",
        lambda _task_id: type("Task", (), {"payload": {"question": "What is 2+2?"}})(),
    )
    monkeypatch.setattr(llm_query_module, "mark_task_in_progress", lambda _task_id: None)
    monkeypatch.setattr(
        llm_query_module,
        "mark_task_completed",
        lambda _task_id, payload: completed_payload.update(payload),
    )
    monkeypatch.setattr(llm_query_module, "mark_task_failed", lambda _task_id, _error: None)
    monkeypatch.setattr(
        llm_query_module,
        "generate_text",
        lambda request: TextGenerationResult(text="4", model="gpt-5-nano"),
    )

    assert llm_query_module.llm_query_task("task-123") == "4"
    assert completed_payload == {"answer": "4", "model": "gpt-5-nano"}


def test_llm_query_task_rejects_blank_question(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        llm_query_module,
        "get_task",
        lambda _task_id: type("Task", (), {"payload": {"question": "   "}})(),
    )
    monkeypatch.setattr(llm_query_module, "mark_task_in_progress", lambda _task_id: None)
    monkeypatch.setattr(llm_query_module, "mark_task_failed", lambda _task_id, _error: None)

    with pytest.raises(ValueError, match="question must not be empty"):
        llm_query_module.llm_query_task("task-123")
