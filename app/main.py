from fastapi import FastAPI

from app.api.routes import health, planning_requests
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.include_router(health.router, prefix=settings.api_v1_prefix, tags=["health"])
    app.include_router(
        planning_requests.router,
        prefix=settings.api_v1_prefix,
        tags=["planning-requests"],
    )

    return app


app = create_app()


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
