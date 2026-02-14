from __future__ import annotations

from fastapi import APIRouter, Query

from ...core_cache import get_iosystem
from ...utils import multiindex_to_nested_dict

router = APIRouter()


@router.get("/hierarchy/regions")
def region_hierarchy(
    year: int = Query(..., ge=1995, le=2100),
    language: str = Query("Deutsch", min_length=1),
) -> dict:
    ios = get_iosystem(year=year, language=language)
    mi = ios.index.region_multiindex
    return {"names": list(mi.names), "tree": multiindex_to_nested_dict(mi)}


@router.get("/hierarchy/sectors")
def sector_hierarchy(
    year: int = Query(..., ge=1995, le=2100),
    language: str = Query("Deutsch", min_length=1),
) -> dict:
    ios = get_iosystem(year=year, language=language)
    mi = ios.index.sector_multiindex_per_region
    return {"names": list(mi.names), "tree": multiindex_to_nested_dict(mi)}


@router.get("/impacts")
def impacts(
    year: int = Query(..., ge=1995, le=2100),
    language: str = Query("Deutsch", min_length=1),
) -> dict:
    ios = get_iosystem(year=year, language=language)

    impacts_df = ios.index.impacts_df
    units_df = ios.index.units_df

    unit_by_impact = {}
    if units_df is not None and "impact" in units_df.columns:
        unit_by_impact = {
            str(row["impact"]): {
                "unit": str(row.get("new unit") or row.get("exiobase unit") or ""),
                "decimal_places": int(row.get("decimal places") or 0),
                "divisor": float(row.get("divisor") or 1.0),
            }
            for _, row in units_df.iterrows()
        }

    items = []
    for impact in impacts_df["impact"].astype(str).tolist():
        meta = unit_by_impact.get(impact, {})
        items.append({"impact": impact, **meta})

    return {"impacts": items}

