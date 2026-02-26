from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query

import pandas as pd

from ...paths import config_dir, fast_database_path
from ...utils import multiindex_to_nested_dict

from src.Index import UnitFormatter

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


@lru_cache(maxsize=8)
def _unit_formatter_for_units_xlsx(path: str) -> UnitFormatter:
    return UnitFormatter.from_excel(path)


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

    color_map: dict[str, str] = {}
    if "color" in impact_sheets:
        try:
            cdf = pd.read_excel(str(impacts_path), sheet_name="color")
            if cdf.shape[1] >= 2:
                color_map = dict(zip(cdf.iloc[:, 0].astype(str).tolist(), cdf.iloc[:, 1].astype(str).tolist()))
        except Exception:
            color_map = {}

    # Canonical keys should always come from the "Exiobase" sheet when possible.
    key_sheet = "Exiobase" if "Exiobase" in impact_sheets else language
    label_sheet = language if language in impact_sheets else key_sheet

    keys = _read_excel_first_col(impacts_path, key_sheet)
    labels = _read_excel_first_col(impacts_path, label_sheet)
    if len(labels) != len(keys):
        labels = list(keys)

    # Units: new schema via UnitFormatter (units.xlsx).
    # We return a default unit label (short) based on the configured default_factor.
    label_source = "impacts.xlsx"
    try:
        uf = _unit_formatter_for_units_xlsx(str(units_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse units.xlsx: {e}") from e

    items = []
    for idx, key in enumerate(keys):
        label = labels[idx] if idx < len(labels) else key

        unit_short = ""
        unit_long = ""
        decimal_places = 2
        base_unit = ""
        chosen_exponent = 0
        chosen_factor = 1.0

        try:
            meta = uf.format_value(str(key), 0.0, language, style="short")
            unit_short = str(meta.get("unit_short") or "").strip()
            unit_long = str(meta.get("unit_long") or "").strip()
            chosen_exponent = int(meta.get("chosen_exponent") or 0)
            chosen_factor = float(meta.get("chosen_factor") or 1.0)

            core = uf._cfg.core_by_key.get(str(key))  # type: ignore[attr-defined]
            base_unit = str(getattr(core, "base_unit", "") or "").strip() if core else ""
            decimal_places = int(getattr(core, "decimals", 2) if core else 2)
        except Exception:
            unit_short = ""

        items.append(
            {
                "key": str(key),
                "label": str(label),
                "unit": unit_short or base_unit,
                "unit_short": unit_short or base_unit,
                "unit_long": unit_long or unit_short or base_unit,
                "color": str(color_map.get(str(key), "") or ""),
                "decimal_places": decimal_places,
                "base_unit": base_unit,
                "default_exponent": chosen_exponent,
                "default_factor": chosen_factor,
            }
        )

    return {
        "impacts": items,
        "key_sheet": key_sheet,
        "label_sheet": label_sheet,
        "label_source": label_source,
    }
