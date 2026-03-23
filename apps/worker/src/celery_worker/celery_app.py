from celery import Celery
from core import get_settings

settings = get_settings()

celery_app = Celery(
    "monorepo-worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.task_default_queue = settings.task_queue
celery_app.autodiscover_tasks(["celery_worker.tasks"])
