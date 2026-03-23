from functools import lru_cache

from celery import Celery
from core import get_settings


@lru_cache(maxsize=1)
def get_celery_client() -> Celery:
    settings = get_settings()
    client = Celery(
        "api-service",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )
    client.conf.task_default_queue = settings.task_queue
    return client


def send_worker_task(task_name: str, task_id: str) -> None:
    settings = get_settings()
    get_celery_client().send_task(
        task_name,
        args=[task_id],
        queue=settings.task_queue,
    )
