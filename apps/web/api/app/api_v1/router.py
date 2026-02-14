from fastapi import APIRouter

from .routes import health, meta

router = APIRouter()

router.include_router(health.router, tags=["health"])
router.include_router(meta.router, prefix="/meta", tags=["meta"])

