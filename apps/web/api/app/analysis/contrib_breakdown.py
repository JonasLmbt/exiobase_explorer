from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from src.SupplyChain import SupplyChain
from src.IOSystem import IOSystem

from .base import StageAnalysisMethod
from .selection_utils import selection_to_indices
from ..impact_mapping import resolve_impact_label


def _units_meta(iosystem: IOSystem, impact_label: str) -> tuple[float, int, str]:
    df = iosystem.index.units_df
    try:
        mask = df.iloc[:, 0].astype(str) == str(impact_label)
        if not mask.any():
            return 1.0, 2, ""
        row = df.loc[mask].iloc[0].tolist()
        divisor = float(row[2]) if row[2] is not None else 1.0
        decimals = int(row[3]) if row[3] is not None else 2
        unit = str(row[4] or "")
        return (divisor or 1.0), max(0, decimals), unit
    except Exception:
        return 1.0, 2, ""


def _round_scaled(v: float, divisor: float, decimals: int) -> float:
    try:
        x = float(v) / float(divisor or 1.0)
    except Exception:
        return 0.0
    r = round(x, int(decimals))
    if r == 0 and x != 0:
        return float(x)
    return float(r)


class ContributionBreakdownMethod(StageAnalysisMethod):
    id = "contrib_breakdown"
    label = "Contribution breakdown"

    def _y_vector(self, *, iosystem: IOSystem, indices: list[int]) -> np.ndarray:
        y_mat = iosystem.Y.values
        diag = np.diag(y_mat).astype(np.float32, copy=False)
        n = diag.shape[0]
        if not indices or len(indices) >= n:
            return diag.copy()
        y = np.zeros(n, dtype=np.float32)
        y[np.asarray(indices, dtype=np.int64)] = diag[np.asarray(indices, dtype=np.int64)]
        return y

    def _stage_output_vector(
        self,
        *,
        iosystem: IOSystem,
        sc: SupplyChain,
        stage_id: str,
        y: np.ndarray,
        job_meta: Optional[Dict[str, Any]] = None,
    ) -> np.ndarray:
        a = iosystem.A.values
        l = iosystem.L.values

        if job_meta is not None:
            job_meta["progress"] = max(float(job_meta.get("progress") or 0.0), 0.45)
            job_meta["message"] = "multiplying"

        ay = a @ y
        ly = l @ y

        raw = np.asarray(iosystem.index.raw_material_indices, dtype=np.int64)
        not_raw = np.asarray(iosystem.index.not_raw_material_indices, dtype=np.int64)

        if not getattr(sc, "regional", False):
            if stage_id == "total":
                return ly
            if stage_id == "retail":
                return y

            if stage_id == "direct_suppliers":
                out = ay
                out[raw] = 0.0
                return out

            if stage_id == "resource_extraction":
                out = ly - y
                out[not_raw] = 0.0
                return out

            # preliminary_products
            out = ly - y - ay
            out[raw] = 0.0
            return out

        # Regional selection: re-assign domestic upstream stages to retail (mirrors Impact.get_regional_impacts).
        region_indices = np.asarray(getattr(iosystem.impact, "region_indices", None) or sc.indices, dtype=np.int64)

        # direct suppliers (A, excluding raw materials)
        ds = ay
        ds[raw] = 0.0

        # resource extraction ((L-I), only raw materials)
        re = ly - y
        re[not_raw] = 0.0

        # preliminary products ((L-I) - direct_suppliers, excluding raw materials)
        pp = (ly - y) - ds
        pp[raw] = 0.0

        # retail (I + domestic upstream re-assigned)
        retail = y.copy()
        retail[region_indices] += ds[region_indices] + re[region_indices] + pp[region_indices]

        # zero out domestic contributions for other categories
        ds[region_indices] = 0.0
        re[region_indices] = 0.0
        pp[region_indices] = 0.0

        if stage_id == "total":
            return ly
        if stage_id == "retail":
            return retail
        if stage_id == "direct_suppliers":
            return ds
        if stage_id == "resource_extraction":
            return re
        return pp

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
            job_meta["progress"] = 0.4
            job_meta["message"] = "computing"

        y = self._y_vector(iosystem=iosystem, indices=indices)
        out = self._stage_output_vector(iosystem=iosystem, sc=sc, stage_id=stage_id, y=y, job_meta=job_meta)

        try:
            s_row = iosystem.impact.S.loc[str(impact_label)]
        except Exception as e:
            return {"ok": False, "error": "impact_not_found", "impact": str(impact_label), "detail": str(e)}

        if isinstance(s_row, pd.DataFrame):
            s_row = s_row.iloc[0]
        s = np.asarray(s_row.to_numpy(), dtype=np.float32)

        # Contribution per emitting sector (origin): impact intensity * output for selected final demand.
        contrib = np.asarray(s, dtype=np.float64) * np.asarray(out, dtype=np.float64)

        total_raw = float(np.nansum(contrib) or 0.0)
        if total_raw == 0.0:
            return {
                "kind": "contrib_table_v1",
                "meta": {
                    "stage_id": stage_id,
                    "dimension": dimension,
                    "impact_key": str(impact_key),
                    "impact_resolved": str(impact_label),
                    "total_raw": 0.0,
                },
                "rows": [],
            }

        region_len = len(getattr(iosystem.index, "region_classification", []) or [])
        mi = iosystem.index.sector_multiindex

        rows: list[dict] = []
        if dimension == "regions":
            # group by region leaf (last region level)
            region_leaf_all = mi.get_level_values(region_len - 1 if region_len else 0).astype(str)
            df = pd.DataFrame({"label": region_leaf_all, "value": contrib})
            grouped = df.groupby("label", as_index=False)["value"].sum().sort_values("value", ascending=False)
            divisor, decimals, unit = _units_meta(iosystem, str(impact_label))
            for _, r in grouped.head(max(1, top_n)).iterrows():
                val = float(r["value"])
                rows.append(
                    {
                        "label": str(r["label"]),
                        "share": float(val / total_raw),
                        "absolute": _round_scaled(val, divisor, decimals),
                    }
                )
            return {
                "kind": "contrib_table_v1",
                "meta": {
                    "stage_id": stage_id,
                    "dimension": dimension,
                    "impact_key": str(impact_key),
                    "impact_resolved": str(impact_label),
                    "total_raw": total_raw,
                    "unit": unit,
                    "divisor": divisor,
                    "decimal_places": decimals,
                },
                "rows": rows,
            }

        # dimension == "sectors": show region-specific sectors (full index leafs)
        sector_leaf_all = mi.get_level_values(-1).astype(str)
        region_leaf_all = mi.get_level_values(region_len - 1 if region_len else 0).astype(str)
        labels = sector_leaf_all + " (" + region_leaf_all + ")"
        df = pd.DataFrame({"label": labels, "value": contrib})
        grouped = df.groupby("label", as_index=False)["value"].sum().sort_values("value", ascending=False)
        divisor, decimals, unit = _units_meta(iosystem, str(impact_label))
        for _, r in grouped.head(max(1, top_n)).iterrows():
            val = float(r["value"])
            rows.append(
                {
                    "label": str(r["label"]),
                    "share": float(val / total_raw),
                    "absolute": _round_scaled(val, divisor, decimals),
                }
            )
        return {
            "kind": "contrib_table_v1",
            "meta": {
                "stage_id": stage_id,
                "dimension": dimension,
                "impact_key": str(impact_key),
                "impact_resolved": str(impact_label),
                "total_raw": total_raw,
                "unit": unit,
                "divisor": divisor,
                "decimal_places": decimals,
            },
            "rows": rows,
        }
