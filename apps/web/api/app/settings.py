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

