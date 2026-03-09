FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY . .
RUN uv sync --package monorepo-worker --dev

CMD ["uv", "run", "--project", "apps/worker", "celery", "-A", "celery_worker.celery_app:celery_app", "worker", "--loglevel=info"]
