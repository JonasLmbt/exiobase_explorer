from __future__ import annotations

import matplotlib
matplotlib.use("Agg")

import time
from typing import Any, Dict

from rq import get_current_job

from .core_cache import get_iosystem
from .utils import fig_to_png_base64


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
    analysis_type = analysis.get("type", "noop")

    if analysis_type == "stage_bubble":
        year = int(payload.get("year", 2022))
        language = str(payload.get("language", "Deutsch"))
        selection = payload.get("selection", {}) or {}
        impacts = list(analysis.get("impacts") or [])

        ios = get_iosystem(year=year, language=language)

        mode = selection.get("mode", "all")
        indices = None
        if mode == "indices":
            indices = [int(x) for x in (selection.get("indices") or [])]
        elif mode == "regions_sectors":
            regions = [int(x) for x in (selection.get("regions") or [])]
            sectors = [int(x) for x in (selection.get("sectors") or [])]
            if regions and sectors:
                n_sectors = int(ios.index.amount_sectors)
                indices = [r * n_sectors + s for r in regions for s in sectors]

        if indices is None:
            indices = list(range(9800))

        from src.SupplyChain import SupplyChain

        sc = SupplyChain(iosystem=ios, indices=indices)

        if job is not None:
            job.meta["progress"] = 0.3
            job.meta["message"] = "rendering"
            job.save_meta()

        fig = sc.plot_bubble_diagram(impacts)
        png_b64 = fig_to_png_base64(fig)

        if job is not None:
            job.meta["progress"] = 1.0
            job.meta["message"] = "done"
            job.save_meta()

        return {"kind": "image_base64", "mime": "image/png", "data": png_b64}

    time.sleep(0.2)

    if job is not None:
        job.meta["progress"] = 1.0
        job.meta["message"] = "done"
        job.save_meta()

    return {"ok": True, "analysis_type": analysis_type, "echo": payload}
