from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from src.SupplyChain import SupplyChain

from ...analysis.selection_utils import selection_to_indices
from ...core_cache import get_iosystem

router = APIRouter()


@router.post("/selection/summary")
def selection_summary(payload: Dict[str, Any]) -> dict:
    year = int(payload.get("year", 2022))
    language = str(payload.get("language", "Deutsch"))
    selection = payload.get("selection", {}) or {}

    ios = get_iosystem(year=year, language=language)
    indices = selection_to_indices(iosystem=ios, selection=selection)
    sc = SupplyChain(iosystem=ios, indices=indices)

    return {
        "year": year,
        "language": language,
        "indices_count": len(indices),
        "supplychain_repr": repr(sc),
        "selection": selection,
    }

