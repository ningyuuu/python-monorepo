from fastapi import FastAPI
from monorepo_core import get_settings

from monorepo_api.routes.health import router as health_router

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Welcome to python-monorepo API"}


app.include_router(health_router)
