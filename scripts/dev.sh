#!/usr/bin/env sh
set -eu

if [ "${1:-}" = "api" ]; then
  exec uv run --project apps/api uvicorn api_service.main:app --reload
fi

if [ "${1:-}" = "worker" ]; then
  exec uv run --project apps/worker celery -A celery_worker.celery_app:celery_app worker --loglevel=info
fi

echo "usage: ./scripts/dev.sh [api|worker]"
exit 1
