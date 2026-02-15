from __future__ import annotations

from typing import Any, Dict, Optional

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

        if stage_id == "total":
            impact_data = sc.iosystem.impact.total
        elif stage_id == "resource_extraction":
            impact_data = sc.iosystem.impact.resource_extraction_regional if sc.regional else sc.iosystem.impact.resource_extraction
        elif stage_id == "preliminary_products":
            impact_data = sc.iosystem.impact.preliminary_products_regional if sc.regional else sc.iosystem.impact.preliminary_products
        elif stage_id == "direct_suppliers":
            impact_data = sc.iosystem.impact.direct_suppliers_regional if sc.regional else sc.iosystem.impact.direct_suppliers
        else:  # retail
            impact_data = sc.iosystem.impact.retail_regional if sc.regional else sc.iosystem.impact.retail

        try:
            mat = impact_data.loc[str(impact_label)]
        except Exception as e:
            return {"ok": False, "error": "impact_not_found", "impact": str(impact_label), "detail": str(e)}

        # mat is a DataFrame (or Series). Make it a DataFrame with columns=sector_multiindex.
        if isinstance(mat, pd.Series):
            mat = mat.to_frame().T

        # Per-column contribution for the chosen selection (sum over rows, keep sector_multiindex columns).
        sub = mat.iloc[:, indices]
        contrib = sub.sum(axis=0)

        total_raw = float(contrib.sum() or 0.0)
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
            region_leaf = [str(mi[i][region_len - 1]) if region_len else str(mi[i][0]) for i in indices]
            df = pd.DataFrame({"label": region_leaf, "value": [float(contrib.iloc[j]) for j in range(len(contrib))]})
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
        sector_leaf = [str(mi[i][-1]) for i in indices]
        region_leaf = [str(mi[i][region_len - 1]) if region_len else str(mi[i][0]) for i in indices]
        labels = [f"{s} ({r})" for s, r in zip(sector_leaf, region_leaf)]
        df = pd.DataFrame({"label": labels, "value": [float(contrib.iloc[j]) for j in range(len(contrib))]})
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

