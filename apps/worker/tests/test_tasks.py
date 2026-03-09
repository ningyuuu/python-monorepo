from celery_worker.tasks import add_numbers_task


def test_add_numbers_task() -> None:
    assert add_numbers_task(2, 3) == 5
