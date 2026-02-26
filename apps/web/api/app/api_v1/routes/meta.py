from __future__ import annotations

import os
import re
from typing import List

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from ...paths import config_dir, fast_database_path, fast_databases_dir

router = APIRouter()


def _available_sheets(path) -> list[str]:
    try:
        with pd.ExcelFile(str(path)) as xls:
            return list(xls.sheet_names)
    except Exception:
        return []


def _pick_sheet(*, requested: str, sheets: list[str]) -> str | None:
    if not sheets:
        return None
    if requested in sheets:
        return requested
    if "English" in sheets:
        return "English"
    if "Exiobase" in sheets:
        return "Exiobase"
    return sheets[0]


def _read_translation_sheet(path, sheet: str) -> dict[str, str]:
    df = pd.read_excel(str(path), sheet_name=sheet)
    if df.shape[1] < 2:
        return {}

    keys = df.iloc[:, 0].astype(str).tolist()
    vals = df.iloc[:, 1].astype(str).tolist()

    out: dict[str, str] = {}
    for i, k in enumerate(keys):
        kk = str(k).strip()
        if not kk or kk.lower() == "nan":
            continue
        vv = str(vals[i] if i < len(vals) else "").strip()
        if vv.lower() == "nan":
            vv = ""
        out[kk] = vv
    return out


@router.get("/years")
def list_years() -> dict:
    years: List[str] = []
    pattern = re.compile(r"FAST_IOT_(\d{4})_pxp$")

    fast_dir = fast_databases_dir()
    if fast_dir.is_dir():
        for item in os.listdir(fast_dir):
            full_path = fast_dir / item
            if not os.path.isdir(full_path):
                continue
            match = pattern.match(item)
            if match:
                years.append(match.group(1))

    years = sorted(set(years), reverse=True)
    return {"years": years}


@router.get("/languages")
def list_languages(year: int = Query(..., ge=1995, le=2100)) -> dict:
    fast_general = fast_database_path(year) / "general.xlsx"
    cfg_general = config_dir() / "general.xlsx"
    if not fast_general.exists() and not cfg_general.exists():
        raise HTTPException(
            status_code=404,
            detail=f"general.xlsx not found for year={year}. Expected at: {fast_general.as_posix()} or {cfg_general.as_posix()}",
        )

    try:
        sheets = []
        if fast_general.exists():
            sheets += _available_sheets(fast_general)
        if cfg_general.exists():
            sheets += _available_sheets(cfg_general)
        # Preserve order while de-duplicating.
        seen = set()
        merged = []
        for s in sheets:
            if s in seen:
                continue
            seen.add(s)
            merged.append(s)
        return {"languages": merged}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read languages: {e}") from e


@router.get("/translations")
def translations(
    year: int = Query(..., ge=1995, le=2100),
    language: str = Query("Deutsch", min_length=1),
) -> dict:
    """
    Return UI translation strings from `general.xlsx`.

    The Excel file contains one sheet per language. Each sheet is expected to have two columns:
    - `exiobase`: canonical key (English-like identifier / UI token)
    - `translation`: localized string
    """
    fast_general = fast_database_path(year) / "general.xlsx"
    cfg_general = config_dir() / "general.xlsx"
    if not fast_general.exists() and not cfg_general.exists():
        raise HTTPException(
            status_code=404,
            detail=f"general.xlsx not found for year={year}. Expected at: {fast_general.as_posix()} or {cfg_general.as_posix()}",
        )

    try:
        sheets = []
        if fast_general.exists():
            sheets += _available_sheets(fast_general)
        if cfg_general.exists():
            sheets += _available_sheets(cfg_general)
        # De-dup while preserving order.
        seen = set()
        merged_sheets = []
        for s in sheets:
            if s in seen:
                continue
            seen.add(s)
            merged_sheets.append(s)

        sheet = _pick_sheet(requested=language, sheets=merged_sheets)
        if not sheet:
            return {"language": language, "translations": {}}

        cfg_dict: dict[str, str] = {}
        fast_dict: dict[str, str] = {}

        if cfg_general.exists() and sheet in _available_sheets(cfg_general):
            cfg_dict = _read_translation_sheet(cfg_general, sheet)
        if fast_general.exists() and sheet in _available_sheets(fast_general):
            fast_dict = _read_translation_sheet(fast_general, sheet)

        # Merge: config provides defaults (incl. new web keys), fast-db overrides when non-empty.
        out = dict(cfg_dict)
        for k, v in fast_dict.items():
            if str(v).strip():
                out[k] = str(v).strip()
        return {"language": sheet, "translations": out}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read translations: {e}") from e
