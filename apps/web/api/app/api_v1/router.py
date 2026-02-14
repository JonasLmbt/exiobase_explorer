from fastapi import APIRouter

from .routes import health, jobs, meta

router = APIRouter()

router.include_router(health.router, tags=["health"])
router.include_router(jobs.router, tags=["jobs"])
router.include_router(meta.router, prefix="/meta", tags=["meta"])
