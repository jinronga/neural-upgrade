from __future__ import annotations

from fastapi import FastAPI

from app.api.api_v1.router import api_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME)

    # Health check
    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    # Include versioned API router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()

