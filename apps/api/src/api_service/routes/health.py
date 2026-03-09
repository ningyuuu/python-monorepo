from contracts import HealthResponse
from core import get_settings
from fastapi import APIRouter
from monorepo_domain import build_status_message

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        message=build_status_message(settings.app_name),
    )
