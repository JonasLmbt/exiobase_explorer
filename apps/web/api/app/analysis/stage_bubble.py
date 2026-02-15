from __future__ import annotations

from typing import Any, Dict, Optional

import matplotlib

matplotlib.use("Agg")

from src.SupplyChain import SupplyChain
from src.IOSystem import IOSystem

from .base import StageAnalysisMethod
from .selection_utils import selection_to_indices
from ..impact_mapping import resolve_impact_label


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
        impacts = [str(x) for x in (analysis.get("impacts") or []) if x]
        if not impacts:
            return {"ok": False, "error": "missing_impacts"}

        indices = selection_to_indices(iosystem=iosystem, selection=selection)

        if job_meta is not None:
            job_meta["progress"] = 0.3
            job_meta["message"] = "rendering"

        sc = SupplyChain(iosystem=iosystem, indices=indices)
        gd = iosystem.index.general_dict
        stage_ids = [
            "resource_extraction",
            "preliminary_products",
            "direct_suppliers",
            "retail",
            "total",
        ]
        stages = [
            gd.get("Resource Extraction", "Resource Extraction"),
            gd.get("Preliminary Products", "Preliminary Products"),
            gd.get("Direct Suppliers", "Direct Suppliers"),
            gd.get("Retail", "Retail"),
            gd.get("Total", "Total"),
        ]

        items = []
        for impact_key in impacts:
            resolved = resolve_impact_label(year=int(iosystem.year), language=iosystem.language, impact_key=impact_key)

            total_abs, unit = sc.total(resolved)
            res_abs, _ = sc.resource_extraction(resolved)
            pre_abs, _ = sc.preliminary_products(resolved)
            direct_abs, _ = sc.direct_suppliers(resolved)
            retail_abs, _ = sc.retail(resolved)

            if total_abs and float(total_abs) != 0.0:
                rel = [
                    float(res_abs) / float(total_abs),
                    float(pre_abs) / float(total_abs),
                    float(direct_abs) / float(total_abs),
                    float(retail_abs) / float(total_abs),
                    1.0,
                ]
            else:
                rel = [0.0, 0.0, 0.0, 0.0, 0.0]

            try:
                color = sc.iosystem.impact.get_color(resolved)
            except Exception:
                color = "#8ab4f8"

            items.append(
                {
                    "key": impact_key,
                    "unit": str(unit or ""),
                    "color": str(color or ""),
                    "relative": rel,
                    "absolute": [
                        float(res_abs),
                        float(pre_abs),
                        float(direct_abs),
                        float(retail_abs),
                        float(total_abs),
                    ],
                }
            )

        return {"kind": "stage_table_v1", "stage_ids": stage_ids, "stages": stages, "impacts": items}
