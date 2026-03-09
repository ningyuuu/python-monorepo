UV ?= uv

.PHONY: sync fmt lint typecheck test dev-api dev-worker

sync:
	$(UV) sync --all-packages --dev

fmt:
	$(UV) run ruff format .

lint:
	$(UV) run ruff check .

typecheck:
	$(UV) run mypy apps packages

test:
	$(UV) run pytest

dev-api:
	$(UV) run --project apps/api uvicorn monorepo_api.main:app --reload

dev-worker:
	$(UV) run --project apps/worker celery -A monorepo_worker.celery_app:celery_app worker --loglevel=info
