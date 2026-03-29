import pytest
from celery_worker.tasks import add_numbers_task
from celery_worker.tasks import llm_query as llm_query_module
from celery_worker.tasks import summarise_doc as summarise_doc_module
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
        lambda request: TextGenerationResult(text="4", model="gpt-5.4-nano"),
    )

    assert llm_query_module.llm_query_task("task-123") == "4"
    assert completed_payload == {"answer": "4", "model": "gpt-5.4-nano"}


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


def test_summarise_doc_task_delegates_to_llm_package(monkeypatch: pytest.MonkeyPatch) -> None:
    completed_payload: dict[str, object] = {}

    monkeypatch.setattr(
        summarise_doc_module,
        "get_task",
        lambda _task_id: type(
            "Task",
            (),
            {"payload": {"blob_link": "doc.txt", "blob_type": "vercel"}},
        )(),
    )
    monkeypatch.setattr(summarise_doc_module, "mark_task_in_progress", lambda _task_id: None)
    monkeypatch.setattr(
        summarise_doc_module,
        "mark_task_completed",
        lambda _task_id, payload: completed_payload.update(payload),
    )
    monkeypatch.setattr(summarise_doc_module, "mark_task_failed", lambda _task_id, _error: None)
    monkeypatch.setattr(summarise_doc_module, "get_bytes", lambda _blob_link: b"Document body")
    monkeypatch.setattr(
        summarise_doc_module,
        "_summarise_text",
        lambda text: "Summary",
    )

    assert summarise_doc_module.summarise_doc_task("task-123") == "Summary"
    assert completed_payload == {"result": "Summary"}


def test_summarise_doc_task_rejects_empty_extracted_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        summarise_doc_module,
        "get_task",
        lambda _task_id: type(
            "Task",
            (),
            {"payload": {"blob_link": "doc.txt", "blob_type": "vercel"}},
        )(),
    )
    monkeypatch.setattr(summarise_doc_module, "mark_task_in_progress", lambda _task_id: None)
    monkeypatch.setattr(summarise_doc_module, "mark_task_failed", lambda _task_id, _error: None)
    monkeypatch.setattr(summarise_doc_module, "get_bytes", lambda _blob_link: b"   ")

    with pytest.raises(ValueError, match="extracted text is empty"):
        summarise_doc_module.summarise_doc_task("task-123")


def test_worker_summarise_text_delegates_to_generate_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_request: list[object] = []

    monkeypatch.setattr(
        summarise_doc_module,
        "generate_text",
        lambda request: (
            captured_request.append(request)
            or TextGenerationResult(text="Summary", model="gpt-5.4-nano")
        ),
    )

    assert summarise_doc_module._summarise_text("  Document body  ") == "Summary"
    request = captured_request[0]
    assert isinstance(request, summarise_doc_module.TextGenerationRequest)
    assert (
        request.system_prompt
        == summarise_doc_module.SUMMARISE_DOC_GENERATION_PARAMS["system_prompt"]
    )
    assert request.user_prompt == "Summarise the following document:\n\nDocument body"
    assert (
        request.max_output_tokens
        == summarise_doc_module.SUMMARISE_DOC_GENERATION_PARAMS["max_output_tokens"]
    )
