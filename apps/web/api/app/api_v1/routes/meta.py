from __future__ import annotations

import os
import re
from typing import List

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from src.IOSystem import IOSystem

router = APIRouter()


@router.get("/years")
def list_years() -> dict:
    ios = IOSystem(year=2022)
    fast_dir = ios.fast_databases_dir

    years: List[str] = []
    pattern = re.compile(r"FAST_IOT_(\d{4})_pxp$")

    if os.path.isdir(fast_dir):
        for item in os.listdir(fast_dir):
            full_path = os.path.join(fast_dir, item)
            if not os.path.isdir(full_path):
                continue
            match = pattern.match(item)
            if match:
                years.append(match.group(1))

    years = sorted(set(years), reverse=True)
    return {"years": years}


@router.get("/languages")
def list_languages(year: int = Query(..., ge=1995, le=2100)) -> dict:
    ios = IOSystem(year=year)
    general_xlsx = os.path.join(ios.current_fast_database_path, "general.xlsx")
    if not os.path.exists(general_xlsx):
        raise HTTPException(
            status_code=404,
            detail=f"general.xlsx not found for year={year}. Expected at: {general_xlsx}",
        )

    try:
        with pd.ExcelFile(general_xlsx) as xls:
            return {"languages": list(xls.sheet_names)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read languages: {e}") from e

