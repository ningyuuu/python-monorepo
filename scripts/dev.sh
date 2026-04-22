#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

export PYTHONPATH="$ROOT_DIR/packages/core/src:$ROOT_DIR/packages/contracts/src:$ROOT_DIR/packages/domain/src:$ROOT_DIR/packages/tasks-db/src:$ROOT_DIR/packages/blob/src:$ROOT_DIR/packages/llm/src:$ROOT_DIR/apps/api/src"

if [ "${1:-}" = "api" ]; then
  exec uv run --project apps/api uvicorn api_service.main:app --reload
fi

if [ "${1:-}" = "worker" ]; then
  exec uv run --project apps/worker celery -A celery_worker.celery_app:celery_app worker --loglevel=info
fi

echo "usage: ./scripts/dev.sh [api|worker]"
exit 1
