from __future__ import annotations

from typing import Any, Dict, Optional

import matplotlib

matplotlib.use("Agg")

from src.SupplyChain import SupplyChain
from src.IOSystem import IOSystem

from ..utils import fig_to_png_base64
from .base import StageAnalysisMethod


class StageBubbleMethod(StageAnalysisMethod):
    id = "stage_bubble"
    label = "Bubble diagram"

    def run(
        self,
        *,
        iosystem: IOSystem,
        selection: Dict[str, Any],
        analysis: Dict[str, Any],
        job_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        impacts = list(analysis.get("impacts") or [])

        mode = selection.get("mode", "all")
        indices = None
        if mode == "indices":
            indices = [int(x) for x in (selection.get("indices") or [])]
        elif mode == "regions_sectors":
            regions = [int(x) for x in (selection.get("regions") or [])]
            sectors = [int(x) for x in (selection.get("sectors") or [])]
            n_sectors = int(iosystem.index.amount_sectors)
            n_regions = int(iosystem.index.amount_regions)
            if regions and sectors:
                indices = [r * n_sectors + s for r in regions for s in sectors]
            elif regions and not sectors:
                indices = [r * n_sectors + s for r in regions for s in range(n_sectors)]
            elif sectors and not regions:
                indices = [r * n_sectors + s for r in range(n_regions) for s in sectors]

        if indices is None:
            indices = list(range(9800))

        if job_meta is not None:
            job_meta["progress"] = 0.3
            job_meta["message"] = "rendering"

        sc = SupplyChain(iosystem=iosystem, indices=indices)
        fig = sc.plot_bubble_diagram(impacts)
        png_b64 = fig_to_png_base64(fig)

        return {"kind": "image_base64", "mime": "image/png", "data": png_b64}
