from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from src.SupplyChain import SupplyChain

from ...analysis.selection_utils import selection_to_indices
from ...core_cache import get_iosystem

router = APIRouter()

def _compress_multiindex_selection(mi, selected: list[int]) -> dict | None:
    """
    Try to express a selection of leaf indices as a single (level_name -> value)
    filter. Returns {} for empty/all selection, None if it cannot be compressed.
    """
    if not selected:
        return {}
    all_idx = set(range(len(mi)))
    sel = set(int(i) for i in selected)
    if sel == all_idx:
        return {}

    for level in mi.names:
        vals = [mi[i][mi.names.index(level)] for i in sel]
        uniq = set(vals)
        if len(uniq) != 1:
            continue
        v = next(iter(uniq))
        level_values = mi.get_level_values(level)
        group_idx = {i for i, lv in enumerate(level_values) if lv == v}
        if sel == group_idx:
            return {str(level): v}
    return None


@router.post("/selection/summary")
def selection_summary(payload: Dict[str, Any]) -> dict:
    year = int(payload.get("year", 2022))
    language = str(payload.get("language", "Deutsch"))
    selection = payload.get("selection", {}) or {}

    ios = get_iosystem(year=year, language=language)

    # Prefer hierarchy-level selection when the user effectively selected exactly one group
    # (e.g., Continent=Europa or Stage=Sekundär). Fall back to indices otherwise.
    use_hierarchy = False
    kwargs: dict[str, Any] = {}
    if selection.get("mode") == "regions_sectors":
        regions = [int(x) for x in (selection.get("regions") or [])]
        sectors = [int(x) for x in (selection.get("sectors") or [])]

        region_kw = _compress_multiindex_selection(ios.index.region_multiindex, regions)
        sector_kw = _compress_multiindex_selection(ios.index.sector_multiindex_per_region, sectors)

        if region_kw is not None and sector_kw is not None:
            kwargs.update(region_kw)
            kwargs.update(sector_kw)
            use_hierarchy = True

    if use_hierarchy:
        sc = SupplyChain(iosystem=ios, **kwargs)
        indices_count = len(sc.indices)
    else:
        indices = selection_to_indices(iosystem=ios, selection=selection)
        sc = SupplyChain(iosystem=ios, indices=indices)
        indices_count = len(indices)

    return {
        "year": year,
        "language": language,
        "indices_count": indices_count,
        "supplychain_repr": repr(sc),
        "selection": selection,
        "selection_mode": "hierarchy" if use_hierarchy else "indices",
        "hierarchy_kwargs": kwargs,
    }
