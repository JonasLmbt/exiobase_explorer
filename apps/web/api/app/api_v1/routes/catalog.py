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


def _read_excel_first_col(path, sheet_name: str) -> list[str]:
    df = pd.read_excel(str(path), sheet_name=sheet_name)
    if df.shape[1] < 1:
        return []
    col0 = df.columns[0]
    return df[col0].astype(str).tolist()


def _available_sheets(path) -> list[str]:
    try:
        with pd.ExcelFile(str(path)) as xls:
            return list(xls.sheet_names)
    except Exception:
        return []


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

    impact_sheets = _available_sheets(impacts_path)
    unit_sheets = _available_sheets(units_path)

    # Canonical keys should always come from the "Exiobase" sheet when possible.
    key_sheet = "Exiobase" if "Exiobase" in impact_sheets else language
    label_sheet = language if language in impact_sheets else key_sheet

    keys = _read_excel_first_col(impacts_path, key_sheet)
    labels = _read_excel_first_col(impacts_path, label_sheet)
    if len(labels) != len(keys):
        labels = list(keys)

    # Units: read same-row meta; use requested language if present for nicer labels.
    unit_sheet = language if language in unit_sheets else ("Exiobase" if "Exiobase" in unit_sheets else None)
    units_df = pd.read_excel(str(units_path), sheet_name=unit_sheet) if unit_sheet else pd.DataFrame()

    # If impacts.xlsx doesn't have a localized sheet, but units.xlsx does, use its first column as labels.
    # For German this is typically "Umweltindikator" and matches what IOSystem matrices use.
    label_source = "impacts.xlsx"
    if label_sheet == key_sheet and unit_sheet == language and not units_df.empty and units_df.shape[1] >= 1:
        ulabels = units_df.iloc[:, 0].astype(str).tolist()
        if len(ulabels) == len(keys):
            labels = ulabels
            label_source = "units.xlsx"

    items = []
    for idx, key in enumerate(keys):
        label = labels[idx] if idx < len(labels) else key
        unit = ""
        divisor = 1.0
        decimal_places = 0

        if not units_df.empty and idx < len(units_df.index) and units_df.shape[1] >= 5:
            row = units_df.iloc[idx]
            try:
                divisor = float(row.iloc[2]) if row.iloc[2] is not None else 1.0
            except Exception:
                divisor = 1.0
            try:
                decimal_places = int(row.iloc[3]) if row.iloc[3] is not None else 0
            except Exception:
                decimal_places = 0
            try:
                unit = str(row.iloc[4] or "")
            except Exception:
                unit = ""

        items.append(
            {
                "key": str(key),
                "label": str(label),
                "unit": unit,
                "decimal_places": decimal_places,
                "divisor": divisor,
            }
        )

    return {
        "impacts": items,
        "key_sheet": key_sheet,
        "label_sheet": label_sheet,
        "unit_sheet": unit_sheet,
        "label_source": label_source,
    }
