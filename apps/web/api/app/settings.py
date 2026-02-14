from __future__ import annotations

import os


def cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [o.strip() for o in raw.split(",") if o.strip()]


def max_active_jobs() -> int:
    try:
        return int(os.environ.get("MAX_ACTIVE_JOBS", "4"))
    except Exception:
        return 4


def use_sync_jobs() -> bool:
    val = (os.environ.get("USE_SYNC_JOBS", "") or "").strip().lower()
    return val in {"1", "true", "yes", "on"}


def sync_job_ttl_seconds() -> int:
    try:
        return int(os.environ.get("SYNC_JOB_TTL_SECONDS", str(60 * 60)))
    except Exception:
        return 60 * 60
