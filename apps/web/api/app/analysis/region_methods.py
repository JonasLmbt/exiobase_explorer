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

        fig = sc.plot_worldmap_by_impact(str(impact), relative=True, show_legend=True, return_data=False)
        return {"kind": "image_base64", "mime": "image/png", "data": fig_to_png_base64(fig)}


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
        fig = sc.plot_topn_by_impacts(impacts=impacts[:4], n=n, relative=True, orientation="vertical", return_data=False)
        return {"kind": "image_base64", "mime": "image/png", "data": fig_to_png_base64(fig)}


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
        fig = sc.plot_flopn_by_impacts(impacts=impacts[:4], n=n, relative=True, orientation="vertical", return_data=False)
        return {"kind": "image_base64", "mime": "image/png", "data": fig_to_png_base64(fig)}


class RegionPieMethod(RegionAnalysisMethod):
    id = "region_pie"
    label = "Pie chart"

    def run(self, *, iosystem: IOSystem, selection: Dict[str, Any], analysis: Dict[str, Any], job_meta=None) -> Dict[str, Any]:
        impact = (analysis.get("impacts") or [None])[0]
        if not impact:
            return {"ok": False, "error": "missing_impact"}

        indices = selection_to_indices(iosystem=iosystem, selection=selection)
        sc = SupplyChain(iosystem=iosystem, indices=indices)
        fig = sc.plot_pie_by_impact(str(impact), relative=True, return_data=False)
        return {"kind": "image_base64", "mime": "image/png", "data": fig_to_png_base64(fig)}
