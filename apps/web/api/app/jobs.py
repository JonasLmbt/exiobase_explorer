from __future__ import annotations

import time
from typing import Any, Dict

from rq import get_current_job

from .analysis.registry import stage_registry
from .core_cache import get_iosystem

# register built-ins
from . import analysis as _analysis_builtin  # noqa: F401


def run_analysis(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Background job entrypoint.

    Supports a first real analysis:
    - `stage_bubble`: bubble diagram (PNG base64)
    """
    job = get_current_job()
    if job is not None:
        job.meta["progress"] = 0.0
        job.meta["message"] = "starting"
        job.save_meta()

    payload = payload or {}
    analysis = payload.get("analysis", {}) or {}
    analysis_type = str(analysis.get("type", "noop"))
    selection = payload.get("selection", {}) or {}

    method = stage_registry.get(analysis_type)
    if method is not None:
        year = int(payload.get("year", 2022))
        language = str(payload.get("language", "Deutsch"))
        ios = get_iosystem(year=year, language=language)

        meta = {}
        result = method.run(iosystem=ios, selection=selection, analysis=analysis, job_meta=meta)
        if job is not None:
            job.meta["progress"] = float(meta.get("progress", 0.9))
            job.meta["message"] = meta.get("message", "done")
            job.save_meta()
        return result

    if job is not None:
        job.meta["progress"] = 1.0
        job.meta["message"] = f"unknown analysis type: {analysis_type}"
        job.save_meta()
    return {"ok": False, "error": "unknown_analysis_type", "analysis_type": analysis_type}

    if job is not None:
        job.meta["progress"] = 1.0
        job.meta["message"] = "done"
        job.save_meta()

    return {"ok": True, "analysis_type": analysis_type, "echo": payload}
