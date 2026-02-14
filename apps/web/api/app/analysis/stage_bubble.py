from __future__ import annotations

from typing import Any, Dict, Optional

import matplotlib

matplotlib.use("Agg")

from src.SupplyChain import SupplyChain
from src.IOSystem import IOSystem

from ..utils import fig_to_png_base64
from .base import StageAnalysisMethod
from .selection_utils import selection_to_indices


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

        indices = selection_to_indices(iosystem=iosystem, selection=selection)

        if job_meta is not None:
            job_meta["progress"] = 0.3
            job_meta["message"] = "rendering"

        sc = SupplyChain(iosystem=iosystem, indices=indices)
        fig = sc.plot_bubble_diagram(impacts)
        png_b64 = fig_to_png_base64(fig)

        return {"kind": "image_base64", "mime": "image/png", "data": png_b64}
