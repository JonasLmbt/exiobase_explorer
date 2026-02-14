from __future__ import annotations

from typing import Any, Dict, Optional

import matplotlib

matplotlib.use("Agg")

from src.SupplyChain import SupplyChain
from src.IOSystem import IOSystem

from ..utils import fig_to_png_base64
from .region_base import RegionAnalysisMethod
from .selection_utils import selection_to_indices


class RegionWorldMapMethod(RegionAnalysisMethod):
    id = "region_world_map"
    label = "World map"

    def run(self, *, iosystem: IOSystem, selection: Dict[str, Any], analysis: Dict[str, Any], job_meta=None) -> Dict[str, Any]:
        impact = (analysis.get("impacts") or [None])[0]
        if not impact:
            return {"ok": False, "error": "missing_impact"}

        indices = selection_to_indices(iosystem=iosystem, selection=selection)
        sc = SupplyChain(iosystem=iosystem, indices=indices)

        fig, world = sc.plot_worldmap_by_impact(str(impact), relative=True, show_legend=False, return_data=True)
        geojson = world.to_json()
        return {
            "kind": "geojson_v1",
            "geojson": geojson,
            "meta": {"impact": str(impact), "relative": True},
        }


class RegionTopNMethod(RegionAnalysisMethod):
    id = "region_topn"
    label = "Top n"

    def run(self, *, iosystem: IOSystem, selection: Dict[str, Any], analysis: Dict[str, Any], job_meta=None) -> Dict[str, Any]:
        impacts = list(analysis.get("impacts") or [])
        if not impacts:
            return {"ok": False, "error": "missing_impacts"}

        n = int((analysis.get("params") or {}).get("n", 10))
        indices = selection_to_indices(iosystem=iosystem, selection=selection)
        sc = SupplyChain(iosystem=iosystem, indices=indices)
        fig, mat = sc.plot_topn_by_impacts(impacts=impacts[:4], n=n, relative=True, orientation="vertical", return_data=True)
        return {
            "kind": "table_v1",
            "meta": {"type": "topn", "n": n, "relative": True},
            "columns": [str(c) for c in mat.columns.tolist()],
            "index": [str(i) for i in mat.index.tolist()],
            "values": [[float(x) for x in row] for row in mat.to_numpy()],
        }


class RegionFlopNMethod(RegionAnalysisMethod):
    id = "region_flopn"
    label = "Flop n"

    def run(self, *, iosystem: IOSystem, selection: Dict[str, Any], analysis: Dict[str, Any], job_meta=None) -> Dict[str, Any]:
        impacts = list(analysis.get("impacts") or [])
        if not impacts:
            return {"ok": False, "error": "missing_impacts"}

        n = int((analysis.get("params") or {}).get("n", 10))
        indices = selection_to_indices(iosystem=iosystem, selection=selection)
        sc = SupplyChain(iosystem=iosystem, indices=indices)
        fig, mat = sc.plot_flopn_by_impacts(impacts=impacts[:4], n=n, relative=True, orientation="vertical", return_data=True)
        return {
            "kind": "table_v1",
            "meta": {"type": "flopn", "n": n, "relative": True},
            "columns": [str(c) for c in mat.columns.tolist()],
            "index": [str(i) for i in mat.index.tolist()],
            "values": [[float(x) for x in row] for row in mat.to_numpy()],
        }


class RegionPieMethod(RegionAnalysisMethod):
    id = "region_pie"
    label = "Pie chart"

    def run(self, *, iosystem: IOSystem, selection: Dict[str, Any], analysis: Dict[str, Any], job_meta=None) -> Dict[str, Any]:
        impact = (analysis.get("impacts") or [None])[0]
        if not impact:
            return {"ok": False, "error": "missing_impact"}

        indices = selection_to_indices(iosystem=iosystem, selection=selection)
        sc = SupplyChain(iosystem=iosystem, indices=indices)
        fig, pie_df = sc.plot_pie_by_impact(str(impact), relative=True, return_data=True)
        return {
            "kind": "pie_v1",
            "meta": {"impact": str(impact), "relative": True},
            "rows": [
                {"label": str(r["label"]), "value": float(r["value"]), "unit": str(r.get("unit") or "")}
                for _, r in pie_df.iterrows()
            ],
        }
