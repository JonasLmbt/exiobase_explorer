from __future__ import annotations

from typing import Any, Dict, Optional

import matplotlib

matplotlib.use("Agg")

from src.SupplyChain import SupplyChain
from src.IOSystem import IOSystem

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
        impacts = [str(x) for x in (analysis.get("impacts") or []) if x]
        if not impacts:
            return {"ok": False, "error": "missing_impacts"}

        indices = selection_to_indices(iosystem=iosystem, selection=selection)

        if job_meta is not None:
            job_meta["progress"] = 0.3
            job_meta["message"] = "rendering"

        sc = SupplyChain(iosystem=iosystem, indices=indices)
        df = sc.calculate_all(impacts=impacts, relative=True, decimal_places=5)

        gd = iosystem.index.general_dict
        stages = [
            gd.get("Resource Extraction", "Resource Extraction"),
            gd.get("Preliminary Products", "Preliminary Products"),
            gd.get("Direct Suppliers", "Direct Suppliers"),
            gd.get("Retail", "Retail"),
            gd.get("Total", "Total"),
        ]

        items = []
        for i, impact_key in enumerate(impacts):
            row = df.iloc[i]
            items.append(
                {
                    "key": impact_key,
                    "unit": str(row.get(gd.get("Unit", "Unit"), "")),
                    "color": str(row.get(gd.get("Color", "Color"), "")),
                    "values": [
                        float(row[stages[0]]),
                        float(row[stages[1]]),
                        float(row[stages[2]]),
                        float(row[stages[3]]),
                        float(row[stages[4]]),
                    ],
                }
            )

        return {"kind": "stage_table_v1", "stages": stages, "impacts": items, "relative": True}
