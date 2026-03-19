from core import get_settings
from fastapi import FastAPI

from api_service.routes.add import router as add_router
from api_service.routes.health import router as health_router
from api_service.routes.query import router as query_router
from api_service.routes.summarise_doc import router as summarise_doc_router

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Welcome to python-monorepo API"}


app.include_router(add_router)
app.include_router(query_router)
app.include_router(summarise_doc_router)
app.include_router(health_router)
