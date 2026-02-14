from __future__ import annotations

import time
from typing import Any, Dict

from rq import get_current_job


def run_analysis(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Background job entrypoint.

    For now this is an MVP stub to validate the queue + result retrieval.
    """
    job = get_current_job()
    if job is not None:
        job.meta["progress"] = 0.0
        job.meta["message"] = "starting"
        job.save_meta()

    analysis = (payload or {}).get("analysis", {}) or {}
    analysis_type = analysis.get("type", "noop")

    time.sleep(0.2)

    if job is not None:
        job.meta["progress"] = 1.0
        job.meta["message"] = "done"
        job.save_meta()

    return {"ok": True, "analysis_type": analysis_type, "echo": payload}

