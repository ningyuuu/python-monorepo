from api_service.main import app
from api_service.routes import extract_data as extract_data_route
from fastapi.testclient import TestClient

client = TestClient(app)


def test_enqueue_extract_data(monkeypatch) -> None:
    monkeypatch.setattr(
        extract_data_route,
        "create_task",
        lambda task_name, payload: type("Task", (), {"id": "task-123"})(),
    )
    monkeypatch.setattr(extract_data_route, "send_worker_task", lambda _name, _task_id: None)

    response = client.post(
        "/tasks/extract_data",
        json={
            "user_link": "https://example.com/doc",
            "blob_link": "https://blob.vercel-storage.com/doc.pdf",
            "blob_type": "vercel",
        },
    )

    assert response.status_code == 202
    assert response.json() == {"task_id": "task-123", "status": "queued"}


def test_get_extract_data_task_status(monkeypatch) -> None:
    monkeypatch.setattr(
        extract_data_route,
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

    response = client.get("/tasks/extract_data/task-123")

    assert response.status_code == 200
    assert response.json() == {
        "task_id": "task-123",
        "status": "completed",
        "result": {"items": []},
        "error": None,
    }
