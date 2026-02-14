from __future__ import annotations

from typing import Any, Dict, Optional

import matplotlib

matplotlib.use("Agg")

from src.SupplyChain import SupplyChain
from src.IOSystem import IOSystem

from ..utils import fig_to_png_base64
from .region_base import RegionAnalysisMethod


def _selection_to_indices(*, iosystem: IOSystem, selection: Dict[str, Any]) -> list[int]:
    mode = selection.get("mode", "all")
    if mode == "indices":
        return [int(x) for x in (selection.get("indices") or [])]

    if mode == "regions_sectors":
        regions = [int(x) for x in (selection.get("regions") or [])]
        sectors = [int(x) for x in (selection.get("sectors") or [])]
        n_sectors = int(iosystem.index.amount_sectors)
        n_regions = int(iosystem.index.amount_regions)
        if regions and sectors:
            return [r * n_sectors + s for r in regions for s in sectors]
        if regions and not sectors:
            return [r * n_sectors + s for r in regions for s in range(n_sectors)]
        if sectors and not regions:
            return [r * n_sectors + s for r in range(n_regions) for s in sectors]

    return list(range(9800))


class RegionWorldMapMethod(RegionAnalysisMethod):
    id = "region_world_map"
    label = "World map"

    def run(self, *, iosystem: IOSystem, selection: Dict[str, Any], analysis: Dict[str, Any], job_meta=None) -> Dict[str, Any]:
        impact = (analysis.get("impacts") or [None])[0]
        if not impact:
            return {"ok": False, "error": "missing_impact"}

        indices = _selection_to_indices(iosystem=iosystem, selection=selection)
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
        indices = _selection_to_indices(iosystem=iosystem, selection=selection)
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
        indices = _selection_to_indices(iosystem=iosystem, selection=selection)
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

        indices = _selection_to_indices(iosystem=iosystem, selection=selection)
        sc = SupplyChain(iosystem=iosystem, indices=indices)
        fig = sc.plot_pie_by_impact(str(impact), relative=True, return_data=False)
        return {"kind": "image_base64", "mime": "image/png", "data": fig_to_png_base64(fig)}

