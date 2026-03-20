# python-monorepo

A Python-native monorepo for a FastAPI service, a Celery worker, and shared internal packages.

## Stack

- `uv` for workspace and dependency management
- `FastAPI` for the HTTP API
- `Celery` for background jobs
- `ruff` for linting and formatting
- `mypy` for type checking
- `pytest` for tests

## Layout

- `apps/api` — FastAPI app
- `apps/worker` — Celery worker
- `packages/core` — shared config and runtime helpers
- `packages/llm` — shared OpenAI client helpers and workflows
- `packages/domain` — reusable domain logic
- `packages/contracts` — shared Pydantic models
- `packages/tasks-db` — shared PostgreSQL task persistence library

## Getting started

1. Install `uv`.
2. Run `make sync`.
3. Copy `.env.example` to `.env` if you want to override defaults.
4. Start PostgreSQL and Redis if you want to run the worker.

## Docker

Each deployable app ships with its own Dockerfile:

- `apps/api/Dockerfile`
- `apps/worker/Dockerfile`

A starter Compose file is available in `infra/compose/docker-compose.yml`.
