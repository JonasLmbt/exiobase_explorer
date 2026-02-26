from __future__ import annotations

from typing import Any, Dict, Optional

from src.SupplyChain import SupplyChain
from src.IOSystem import IOSystem

from .base import StageAnalysisMethod
from .selection_utils import selection_to_indices
from ..impact_mapping import resolve_impact_label


class ContributionBreakdownMethod(StageAnalysisMethod):
    id = "contrib_breakdown"
    label = "Contribution breakdown"

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

        params = analysis.get("params") or {}
        stage_id = str(params.get("stage_id") or "").strip()
        dimension = str(params.get("dimension") or "").strip().lower()
        top_n = int(params.get("top_n") or 25)
        if stage_id not in {"resource_extraction", "preliminary_products", "direct_suppliers", "retail", "total"}:
            return {"ok": False, "error": "invalid_stage_id", "stage_id": stage_id}
        if dimension not in {"regions", "sectors"}:
            return {"ok": False, "error": "invalid_dimension", "dimension": dimension}

        indices = selection_to_indices(iosystem=iosystem, selection=selection)
        sc = SupplyChain(iosystem=iosystem, indices=indices)

        impact_key = impacts[0]
        impact_label = resolve_impact_label(year=int(iosystem.year), language=iosystem.language, impact_key=impact_key)

        if job_meta is not None:
            job_meta["progress"] = 0.55
            job_meta["message"] = "computing"

        res = sc.contribution_breakdown_table(
            impact=str(impact_label),
            stage_id=stage_id,
            dimension=dimension,
            top_n=top_n,
        )

        # Keep API metadata stable.
        if isinstance(res, dict) and res.get("kind") == "contrib_table_v1":
            meta = dict(res.get("meta") or {})
            meta["impact_key"] = str(impact_key)
            meta["impact_resolved"] = str(impact_label)
            res["meta"] = meta
        return res
