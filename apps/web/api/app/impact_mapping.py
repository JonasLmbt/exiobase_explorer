from __future__ import annotations

from functools import lru_cache

import pandas as pd

from .paths import config_dir, fast_database_path


def _pick_impacts_xlsx(year: int):
    fast = fast_database_path(year) / "impacts.xlsx"
    if fast.exists():
        return fast
    return config_dir() / "impacts.xlsx"


def _read_first_col(path, sheet_name: str) -> list[str]:
    df = pd.read_excel(str(path), sheet_name=sheet_name)
    if df.shape[1] < 1:
        return []
    return df.iloc[:, 0].astype(str).tolist()


def _sheets(path) -> list[str]:
    with pd.ExcelFile(str(path)) as xls:
        return list(xls.sheet_names)


@lru_cache(maxsize=32)
def impact_key_to_label_map(*, year: int, language: str) -> dict[str, str]:
    """
    Map canonical impact keys (from sheet "Exiobase") to localized labels (from `language` sheet).
    Falls back safely if sheets are missing.
    """
    path = _pick_impacts_xlsx(year)
    sheets = _sheets(path)

    key_sheet = "Exiobase" if "Exiobase" in sheets else (language if language in sheets else sheets[0])
    label_sheet = language if language in sheets else key_sheet

    keys = _read_first_col(path, key_sheet)
    labels = _read_first_col(path, label_sheet)
    if len(labels) != len(keys):
        labels = list(keys)

    return {k: labels[i] for i, k in enumerate(keys)}


def resolve_impact_label(*, year: int, language: str, impact_key: str) -> str:
    if not impact_key:
        return impact_key
    if (language or "").casefold() == "exiobase":
        return impact_key
    return impact_key_to_label_map(year=year, language=language).get(impact_key, impact_key)

