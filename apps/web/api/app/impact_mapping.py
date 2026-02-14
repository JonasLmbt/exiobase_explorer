from __future__ import annotations

from functools import lru_cache

import pandas as pd

from .paths import config_dir, fast_database_path


def _pick_impacts_xlsx(year: int):
    fast = fast_database_path(year) / "impacts.xlsx"
    if fast.exists():
        return fast
    return config_dir() / "impacts.xlsx"

def _pick_units_xlsx(year: int):
    fast = fast_database_path(year) / "units.xlsx"
    if fast.exists():
        return fast
    return config_dir() / "units.xlsx"


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
    Map canonical impact keys (sheet "Exiobase") to localized labels (sheet `language`).

    Preferred source is `units.xlsx` because:
    - SupplyChain.transform_unit() uses units_df col0 as impact identifier
    - labels in units.xlsx tend to match IOSystem language-specific matrices

    Falls back safely if sheets are missing.
    """
    def build_from(path) -> dict[str, str] | None:
        if not path.exists():
            return None
        sheets = _sheets(path)
        if not sheets:
            return None

        key_sheet = "Exiobase" if "Exiobase" in sheets else (sheets[0])
        label_sheet = language if language in sheets else key_sheet

        keys = _read_first_col(path, key_sheet)
        labels = _read_first_col(path, label_sheet)
        if not keys:
            return None
        if len(labels) != len(keys):
            labels = list(keys)
        return {str(k): str(labels[i]) for i, k in enumerate(keys)}

    m = build_from(_pick_units_xlsx(year))
    if m:
        return m

    m = build_from(_pick_impacts_xlsx(year))
    if m:
        return m
    return {}


def resolve_impact_label(*, year: int, language: str, impact_key: str) -> str:
    if not impact_key:
        return impact_key
    if (language or "").casefold() == "exiobase":
        return impact_key
    key = str(impact_key).strip()
    m = impact_key_to_label_map(year=year, language=language)
    if key in m:
        return m[key]
    # Try a normalized lookup to tolerate small whitespace differences.
    nmap = {k.strip(): v for k, v in m.items()}
    return nmap.get(key, impact_key)
