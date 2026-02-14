from __future__ import annotations

from typing import Any, Dict

from src.IOSystem import IOSystem


def selection_to_indices(*, iosystem: IOSystem, selection: Dict[str, Any]) -> list[int]:
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

