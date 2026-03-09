from monorepo_domain import add_numbers

from monorepo_worker.celery_app import celery_app


@celery_app.task(name="monorepo_worker.add_numbers")
def add_numbers_task(a: int, b: int) -> int:
    return add_numbers(a, b)
