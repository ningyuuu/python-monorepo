from api_service.main import app
from api_service.routes import extract_quote as extract_quote_route
from fastapi.testclient import TestClient

client = TestClient(app)


def test_enqueue_extract_quote(monkeypatch) -> None:
    monkeypatch.setattr(
        extract_quote_route,
        "create_task",
        lambda task_name, payload, email: type("Task", (), {"id": "task-123"})(),
    )
    monkeypatch.setattr(
        extract_quote_route, "send_worker_task", lambda _name, _task_id: None
    )

    response = client.post(
        "/tasks/extract_quote",
        json={
            "user_link": "https://example.com/doc",
            "blob_link": "https://blob.vercel-storage.com/doc.pdf",
            "blob_type": "vercel",
            "email": "person@example.com",
        },
    )

    assert response.status_code == 202
    assert response.json() == {"task_id": "task-123", "status": "queued"}


def test_enqueue_extract_quote_rejects_invalid_email() -> None:
    response = client.post(
        "/tasks/extract_quote",
        json={
            "user_link": "https://example.com/doc",
            "blob_link": "https://blob.vercel-storage.com/doc.pdf",
            "blob_type": "vercel",
            "email": "not-an-email",
        },
    )

    assert response.status_code == 422


def test_get_extract_quote_task_status(monkeypatch) -> None:
    monkeypatch.setattr(
        extract_quote_route,
        "get_task",
        lambda _task_id: type(
            "Task",
            (),
            {
                "id": "task-123",
                "status": "completed",
                "result": {"items": []},
                "error": None,
            },
        )(),
    )

    response = client.get("/tasks/extract_quote/task-123")

    assert response.status_code == 200
    assert response.json() == {
        "task_id": "task-123",
        "status": "completed",
        "result": {"items": []},
        "error": None,
    }
