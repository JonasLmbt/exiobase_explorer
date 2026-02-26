from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from src.SupplyChain import SupplyChain
from src.IOSystem import IOSystem

from .region_base import RegionAnalysisMethod
from .selection_utils import selection_to_indices
from ..impact_mapping import resolve_impact_label



class RegionContributionMethod(RegionAnalysisMethod):
    id = "region_contrib"
    label = "Region contribution breakdown"

    def run(
        self,
        *,
        iosystem: IOSystem,
        selection: Dict[str, Any],
        analysis: Dict[str, Any],
        job_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        impact_key = (analysis.get("impacts") or [None])[0]
        if not impact_key:
            return {"ok": False, "error": "missing_impact"}

        params = analysis.get("params") or {}
        region_exiobase = str(params.get("region_exiobase") or "").strip()
        top_n = int(params.get("top_n") or 30)
        if not region_exiobase:
            return {"ok": False, "error": "missing_region_exiobase"}

        indices = selection_to_indices(iosystem=iosystem, selection=selection)
        sc = SupplyChain(iosystem=iosystem, indices=indices)

        resolved = resolve_impact_label(year=int(iosystem.year), language=iosystem.language, impact_key=str(impact_key))
        if job_meta is not None:
            job_meta["progress"] = 0.55
            job_meta["message"] = "computing"

        res = sc.region_contribution_table(impact=str(resolved), region_exiobase=region_exiobase, top_n=top_n)
        # Keep API metadata stable.
        if isinstance(res, dict) and res.get("kind") == "contrib_table_v1":
            meta = dict(res.get("meta") or {})
            meta["impact_key"] = str(impact_key)
            meta["impact_resolved"] = str(resolved)
            res["meta"] = meta
        return res
