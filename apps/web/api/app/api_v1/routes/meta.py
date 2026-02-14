from __future__ import annotations

import os
import re
from typing import List

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from ...paths import fast_database_path, fast_databases_dir

router = APIRouter()


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
    general_xlsx = fast_database_path(year) / "general.xlsx"
    if not general_xlsx.exists():
        raise HTTPException(
            status_code=404,
            detail=f"general.xlsx not found for year={year}. Expected at: {general_xlsx.as_posix()}",
        )

    try:
        with pd.ExcelFile(str(general_xlsx)) as xls:
            return {"languages": list(xls.sheet_names)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read languages: {e}") from e
