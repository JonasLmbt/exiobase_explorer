from fastapi import APIRouter

from .routes import catalog, health, jobs, meta, selection

router = APIRouter()

router.include_router(health.router, tags=["health"])
router.include_router(jobs.router, tags=["jobs"])
router.include_router(meta.router, prefix="/meta", tags=["meta"])
router.include_router(catalog.router, tags=["catalog"])
router.include_router(selection.router, tags=["selection"])
