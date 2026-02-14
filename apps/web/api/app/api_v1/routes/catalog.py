from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

import pandas as pd

from ...paths import config_dir, fast_database_path
from ...utils import multiindex_to_nested_dict

router = APIRouter()


def _leaves_from_df(df: pd.DataFrame) -> list[dict]:
    leaves = []
    for i, row in df.iterrows():
        path = [str(row[col]) for col in df.columns]
        leaves.append({"index": int(i), "path": path})
    return leaves


@router.get("/hierarchy/regions")
def region_hierarchy(
    year: int = Query(..., ge=1995, le=2100),
    language: str = Query("Deutsch", min_length=1),
) -> dict:
    db = fast_database_path(year)
    path = db / "regions.xlsx"
    if not path.exists():
        path = config_dir() / "regions.xlsx"
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"regions.xlsx not found: {path.as_posix()}")
    df = pd.read_excel(str(path), sheet_name=language).iloc[:, ::-1]
    mi = pd.MultiIndex.from_arrays([df[col] for col in df.columns], names=df.columns.tolist())
    return {"names": list(mi.names), "tree": multiindex_to_nested_dict(mi), "leaves": _leaves_from_df(df)}


@router.get("/hierarchy/sectors")
def sector_hierarchy(
    year: int = Query(..., ge=1995, le=2100),
    language: str = Query("Deutsch", min_length=1),
) -> dict:
    db = fast_database_path(year)
    path = db / "sectors.xlsx"
    if not path.exists():
        path = config_dir() / "sectors.xlsx"
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"sectors.xlsx not found: {path.as_posix()}")
    df = pd.read_excel(str(path), sheet_name=language).iloc[:, ::-1]
    mi = pd.MultiIndex.from_arrays([df[col] for col in df.columns], names=df.columns.tolist())
    return {"names": list(mi.names), "tree": multiindex_to_nested_dict(mi), "leaves": _leaves_from_df(df)}


@router.get("/impacts")
def impacts(
    year: int = Query(..., ge=1995, le=2100),
    language: str = Query("Deutsch", min_length=1),
) -> dict:
    db = fast_database_path(year)
    impacts_path = db / "impacts.xlsx"
    units_path = db / "units.xlsx"
    if not impacts_path.exists():
        impacts_path = config_dir() / "impacts.xlsx"
        if not impacts_path.exists():
            raise HTTPException(status_code=404, detail=f"impacts.xlsx not found: {impacts_path.as_posix()}")
    if not units_path.exists():
        units_path = config_dir() / "units.xlsx"
        if not units_path.exists():
            raise HTTPException(status_code=404, detail=f"units.xlsx not found: {units_path.as_posix()}")

    impacts_df = pd.read_excel(str(impacts_path), sheet_name=language)
    units_df = pd.read_excel(str(units_path), sheet_name=language)

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
