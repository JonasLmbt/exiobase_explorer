from fastapi import APIRouter

from ...paths import config_dir, databases_dir, fast_database_path, fast_databases_dir
from ...settings import use_sync_jobs

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/health/details")
def health_details(year: int = 2022) -> dict:
    db_dir = databases_dir()
    fast_dir = fast_databases_dir()
    fast_year = fast_database_path(year)
    cfg = config_dir()

    def e(p):
        try:
            return p.exists()
        except Exception:
            return False

    return {
        "status": "ok",
        "use_sync_jobs": use_sync_jobs(),
        "databases_dir": db_dir.as_posix(),
        "fast_databases_dir": fast_dir.as_posix(),
        "fast_database_path": fast_year.as_posix(),
        "config_dir": cfg.as_posix(),
        "fast_exists": e(fast_year),
        "files": {
            "fast/general.xlsx": e(fast_year / "general.xlsx"),
            "fast/regions.xlsx": e(fast_year / "regions.xlsx"),
            "fast/sectors.xlsx": e(fast_year / "sectors.xlsx"),
            "fast/impacts.xlsx": e(fast_year / "impacts.xlsx"),
            "fast/units.xlsx": e(fast_year / "units.xlsx"),
            "config/general.xlsx": e(cfg / "general.xlsx"),
            "config/regions.xlsx": e(cfg / "regions.xlsx"),
            "config/sectors.xlsx": e(cfg / "sectors.xlsx"),
            "config/impacts.xlsx": e(cfg / "impacts.xlsx"),
            "config/units.xlsx": e(cfg / "units.xlsx"),
        },
    }
