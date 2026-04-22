FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/packages/core/src:/app/packages/contracts/src:/app/packages/domain/src:/app/packages/tasks-db/src:/app/apps/api/src

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY . .

RUN uv sync

EXPOSE 8000

CMD uv run --project apps/api uvicorn api_service.main:app --host 0.0.0.0 --port 8000