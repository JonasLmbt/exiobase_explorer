from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from src.SupplyChain import SupplyChain
from src.IOSystem import IOSystem

from .region_base import RegionAnalysisMethod
from .selection_utils import selection_to_indices
from ..impact_mapping import resolve_impact_label
from .contrib_breakdown import _round_scaled, _units_meta


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
            job_meta["progress"] = 0.3
            job_meta["message"] = "preparing"

        # y: final demand vector for the selected indices (diagonal of Y).
        y_mat = iosystem.Y.values
        diag = np.diag(y_mat).astype(np.float32, copy=False)
        n = diag.shape[0]
        if not indices or len(indices) >= n:
            y = diag.copy()
        else:
            y = np.zeros(n, dtype=np.float32)
            idx = np.asarray(indices, dtype=np.int64)
            y[idx] = diag[idx]

        if job_meta is not None:
            job_meta["progress"] = 0.55
            job_meta["message"] = "multiplying"

        # Total output vector across the supply chain: x = L @ y
        x = iosystem.L.values @ y

        try:
            s_row = iosystem.impact.S.loc[str(resolved)]
        except Exception as e:
            return {"ok": False, "error": "impact_not_found", "impact": str(resolved), "detail": str(e)}

        if isinstance(s_row, pd.DataFrame):
            s_row = s_row.iloc[0]
        s = np.asarray(s_row.to_numpy(), dtype=np.float32)

        contrib = np.asarray(s, dtype=np.float64) * np.asarray(x, dtype=np.float64)

        # Filter emitting sectors to the clicked region.
        region_len = len(getattr(iosystem.index, "region_classification", []) or [])
        mi = iosystem.index.sector_multiindex

        code2name = dict(zip(getattr(iosystem, "regions_exiobase", []) or [], getattr(iosystem, "regions", []) or []))
        region_name = code2name.get(region_exiobase, region_exiobase)

        region_leaf = mi.get_level_values(region_len - 1 if region_len else 0).astype(str)
        mask = region_leaf == str(region_name)
        if not bool(getattr(mask, "any")()):  # pandas Index bool
            # Fallback: sometimes the multiindex may store the code itself
            mask = region_leaf == str(region_exiobase)
        if not bool(getattr(mask, "any")()):
            return {"ok": False, "error": "region_not_found_in_index", "region_exiobase": region_exiobase, "region": region_name}

        contrib_region = contrib[mask.to_numpy(dtype=bool)]
        if contrib_region.size == 0:
            return {"kind": "contrib_table_v1", "meta": {"region_exiobase": region_exiobase, "region": region_name}, "rows": []}

        # Group by sector leaf inside the region.
        sector_leaf = mi.get_level_values(-1).astype(str)[mask]
        df = pd.DataFrame({"label": sector_leaf.to_numpy(), "value": contrib_region})
        grouped = df.groupby("label", as_index=False)["value"].sum().sort_values("value", ascending=False)

        total_raw = float(np.nansum(grouped["value"].to_numpy()) or 0.0)
        divisor, decimals, unit = _units_meta(iosystem, str(resolved))

        rows: list[dict] = []
        for _, r in grouped.head(max(1, top_n)).iterrows():
            val = float(r["value"])
            rows.append(
                {
                    "label": str(r["label"]),
                    "share": float(val / total_raw) if total_raw else 0.0,
                    "absolute": _round_scaled(val, divisor, decimals),
                }
            )

        return {
            "kind": "contrib_table_v1",
            "meta": {
                "impact_key": str(impact_key),
                "impact_resolved": str(resolved),
                "region_exiobase": str(region_exiobase),
                "region": str(region_name),
                "unit": unit,
                "divisor": divisor,
                "decimal_places": decimals,
                "total_raw": total_raw,
            },
            "rows": rows,
        }

