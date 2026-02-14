from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api_v1.router import router as api_v1_router
from .settings import cors_origins


def create_app() -> FastAPI:
    app = FastAPI(
        title="EXIOBASE Explorer API",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router, prefix="/api/v1")
    return app


app = create_app()
