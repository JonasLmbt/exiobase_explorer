"""
Index.py

Contains the IOSystem Index class (extracted from IOSystem.py) and the unit display
scaling + i18n formatting code (previously in unit_display.py).

The unit formatter is optional and only used for UI display.
"""

from __future__ import annotations



import itertools

import logging

import os

import shutil
import unicodedata

from typing import Dict, List, Optional, Tuple, Union



import geopandas as gpd

import numpy as np

import pandas as pd



from dataclasses import dataclass
import math
import re
from typing import Any, Callable, Dict, Literal, Optional, Tuple

import pandas as pd

LabelStyle = Literal["short", "long"]

_EXP_COL_RE = re.compile(r"^1e(-?\d+)_(short|long)$")
_DEFAULT_FACTOR_RE = re.compile(r"^1e([+-]?\d+)$", re.IGNORECASE)


def _is_missing(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return True
    s = str(v).strip()
    return s == "" or s.lower() == "nan"


def _cell_str(v: Any) -> str:
    """Convert an Excel cell value to a clean string, treating NaN/None/empty as ''."""
    return "" if _is_missing(v) else str(v).strip()


def _norm_lang(lang: str) -> str:
    raw = (lang or "").strip()
    if not raw:
        return "en"
    low = raw.casefold()
    if low.startswith("de"):
        return "de"
    if low.startswith("en"):
        return "en"
    if low.startswith("fr"):
        return "fr"
    if low.startswith("es"):
        return "es"
    # Accept already-normalized codes, otherwise default to "en".
    if low in {"de", "en", "fr", "es"}:
        return low
    return "en"


def _parse_default_factor(s: Any) -> Optional[int]:
    if _is_missing(s):
        return None
    # Excel might store "1e6" as a number; accept numeric powers of ten.
    if isinstance(s, (int, float)) and math.isfinite(float(s)) and float(s) > 0:
        v = float(s)
        exp = int(round(math.log10(v)))
        if math.isfinite(exp):
            try:
                if math.isclose(v, 10.0**exp, rel_tol=0.0, abs_tol=max(1e-12, abs(v) * 1e-12)):
                    return exp
            except Exception:
                pass
        return None
    m = _DEFAULT_FACTOR_RE.match(str(s).strip())
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _format_number(
    value: float,
    *,
    decimals: int,
    thousand_sep: str,
    decimal_sep: str,
) -> str:
    # Avoid "-0.00"
    if abs(value) == 0:
        value = 0.0
    try:
        s = f"{value:,.{int(decimals)}f}"
    except Exception:
        s = str(value)
    # Python uses "," thousands and "." decimal separators. Convert.
    s = s.replace(",", "\x00").replace(".", decimal_sep).replace("\x00", thousand_sep)
    return s


@dataclass(frozen=True)
class CoreUnitRow:
    impact_key: str
    source_unit: str
    base_unit: str
    source_to_base: float
    scale_mode: Literal["auto", "fixed"]
    default_exponent: Optional[int]
    min_display: float
    max_display: float
    decimals: int


@dataclass(frozen=True)
class ImpactLangRow:
    impact_key: str
    family_key: str
    base_short: str
    base_long: str
    suffix_short: str
    suffix_long: str


@dataclass(frozen=True)
class Separators:
    thousand: str
    decimal: str


class UnitsConfigError(ValueError):
    """Raised when `units.xlsx` cannot be parsed or validated."""


class UnitsConfig:
    """
    Parsed representation of the `units.xlsx` configuration.

    Attributes:
        core_by_key: impact_key -> CoreUnitRow
        separators_by_lang: lang -> Separators
        impact_lang_by_lang: lang -> impact_key -> ImpactLangRow
        families_by_lang: lang -> family_key -> exponent -> {"short": str, "long": str}
    """

    def __init__(
        self,
        *,
        core_by_key: Dict[str, CoreUnitRow],
        separators_by_lang: Dict[str, Separators],
        impact_lang_by_lang: Dict[str, Dict[str, ImpactLangRow]],
        families_by_lang: Dict[str, Dict[str, Dict[int, Dict[str, str]]]],
    ) -> None:
        self.core_by_key = dict(core_by_key)
        self.separators_by_lang = dict(separators_by_lang)
        self.impact_lang_by_lang = {k: dict(v) for k, v in impact_lang_by_lang.items()}
        self.families_by_lang = families_by_lang

    @staticmethod
    def _read_sheet(path: str, name: str) -> pd.DataFrame:
        try:
            return pd.read_excel(path, sheet_name=name)
        except Exception as e:
            raise UnitsConfigError(f"Failed to read sheet '{name}' from '{path}': {e}") from e

    @classmethod
    def from_excel(cls, path: str) -> "UnitsConfig":
        try:
            with pd.ExcelFile(path) as xls:
                sheets = list(xls.sheet_names)
        except Exception as e:
            raise UnitsConfigError(f"Failed to open units.xlsx: {path}: {e}") from e

        # Resolve sheet names case-insensitively (and accent-insensitively for user convenience).
        by_low = {str(s).strip().casefold(): str(s) for s in sheets}

        def _strip_accents(s: str) -> str:
            return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))

        by_ascii = {_strip_accents(k): v for k, v in by_low.items()}

        def _get_sheet(*names: str) -> Optional[str]:
            for n in names:
                if not n:
                    continue
                key = str(n).strip().casefold()
                if key in by_low:
                    return by_low[key]
                key2 = _strip_accents(key)
                if key2 in by_ascii:
                    return by_ascii[key2]
            return None

        exiobase_sheet = _get_sheet("exiobase")
        if not exiobase_sheet:
            raise UnitsConfigError("Missing required sheet 'exiobase'.")

        core_df = cls._read_sheet(path, exiobase_sheet)
        req = [
            "impact_key",
            "source_unit",
            "base_unit",
            "source_to_base",
            "scale_mode",
            "default_factor",
            "min_display",
            "max_display",
            "decimals",
        ]
        missing = [c for c in req if c not in core_df.columns]
        if missing:
            raise UnitsConfigError(f"Sheet 'exiobase' is missing columns: {missing}")

        core_by_key: Dict[str, CoreUnitRow] = {}
        for _, r in core_df.iterrows():
            key = _cell_str(r.get("impact_key"))
            if not key:
                continue
            if key in core_by_key:
                raise UnitsConfigError(f"Duplicate impact_key in 'exiobase': {key}")
            scale_mode = _cell_str(r.get("scale_mode")).lower() or "auto"
            if scale_mode not in {"auto", "fixed"}:
                scale_mode = "auto"
            default_exp = _parse_default_factor(r.get("default_factor"))
            try:
                source_to_base = float(r.get("source_to_base") or 1.0)
            except Exception:
                source_to_base = 1.0
            try:
                min_display = float(r.get("min_display") or 0.1)
            except Exception:
                min_display = 0.1
            try:
                max_display = float(r.get("max_display") or 1000.0)
            except Exception:
                max_display = 1000.0
            try:
                decimals = int(r.get("decimals") if r.get("decimals") is not None else 2)
            except Exception:
                decimals = 2

            core_by_key[key] = CoreUnitRow(
                impact_key=key,
                source_unit=_cell_str(r.get("source_unit")),
                base_unit=_cell_str(r.get("base_unit")) or _cell_str(r.get("source_unit")),
                source_to_base=source_to_base,
                scale_mode=scale_mode,  # type: ignore[arg-type]
                default_exponent=default_exp,
                min_display=min_display,
                max_display=max_display,
                decimals=max(0, decimals),
            )

        if not core_by_key:
            raise UnitsConfigError("Sheet 'exiobase' has no impact_key rows.")

        separators_by_lang: Dict[str, Separators] = {}
        sep_sheet = _get_sheet("separators")
        if sep_sheet:
            sep_df = cls._read_sheet(path, sep_sheet)
            # Accept either `lang` (spec) or `language` (older user files) as the language column.
            lang_col = "lang" if "lang" in sep_df.columns else ("language" if "language" in sep_df.columns else "")
            if lang_col and "thousand_separator" in sep_df.columns and "decimal_separator" in sep_df.columns:
                for _, r in sep_df.iterrows():
                    lang = _norm_lang(str(r.get(lang_col) or ""))
                    thousand = _cell_str(r.get("thousand_separator"))
                    decimal = _cell_str(r.get("decimal_separator")) or "."
                    separators_by_lang[lang] = Separators(thousand=thousand, decimal=decimal)
        separators_by_lang.setdefault("en", Separators(thousand=",", decimal="."))

        # Language impact mapping sheets.
        #
        # Internally we normalize languages to ISO-like codes ("de", "en", "fr", "es") via `_norm_lang()`,
        # but the Excel sheets are named human-readable ("Deutsch", "English", ...). We resolve those sheet
        # names case-insensitively here and store them under the normalized language codes.
        lang_sheet_by_code = {
            "de": by_low.get("deutsch"),
            "en": by_low.get("english"),
            "fr": by_low.get("français") or by_low.get("francais"),
            "es": by_low.get("español") or by_low.get("espanol"),
        }

        # Prefer accent-insensitive lookup to match both "Français" and "Francais", etc.
        _lang_sheet_by_code = {
            "de": _get_sheet("deutsch"),
            "en": _get_sheet("english"),
            "fr": _get_sheet("francais"),
            "es": _get_sheet("espanol"),
        }

        impact_lang_by_lang: Dict[str, Dict[str, ImpactLangRow]] = {}
        for code, sheet in _lang_sheet_by_code.items():
            if not sheet:
                continue
            df = cls._read_sheet(path, sheet)
            for col in ("impact_key", "family_key", "base_short", "base_long", "suffix_short", "suffix_long"):
                if col not in df.columns:
                    raise UnitsConfigError(f"Sheet '{sheet}' is missing column '{col}'.")
            m: Dict[str, ImpactLangRow] = {}
            for _, r in df.iterrows():
                key = _cell_str(r.get("impact_key"))
                if not key:
                    continue
                if key not in core_by_key:
                    raise UnitsConfigError(f"impact_key '{key}' present in '{sheet}' but missing in 'exiobase'.")
                m[key] = ImpactLangRow(
                    impact_key=key,
                    family_key=_cell_str(r.get("family_key")),
                    base_short=_cell_str(r.get("base_short")),
                    base_long=_cell_str(r.get("base_long")),
                    suffix_short=_cell_str(r.get("suffix_short")),
                    suffix_long=_cell_str(r.get("suffix_long")),
                )
            impact_lang_by_lang[code] = m

        # Family label sheets.
        families_by_lang: Dict[str, Dict[str, Dict[int, Dict[str, str]]]] = {}
        for code, base_sheet in _lang_sheet_by_code.items():
            if not base_sheet:
                continue
            fam_sheet = by_low.get(f"{base_sheet.casefold()}_families")
            if not fam_sheet:
                continue
            df = cls._read_sheet(path, fam_sheet)
            if "family_key" not in df.columns:
                raise UnitsConfigError(f"Sheet '{fam_sheet}' is missing column 'family_key'.")

            exp_cols: Dict[Tuple[int, str], str] = {}
            for col in df.columns:
                m = _EXP_COL_RE.match(str(col).strip())
                if not m:
                    continue
                exp = int(m.group(1))
                style = m.group(2)
                exp_cols[(exp, style)] = str(col)

            fam_map: Dict[str, Dict[int, Dict[str, str]]] = {}
            for _, r in df.iterrows():
                fam = _cell_str(r.get("family_key"))
                if not fam:
                    continue
                exps: Dict[int, Dict[str, str]] = {}
                for (exp, style), col in exp_cols.items():
                    val = r.get(col)
                    if _is_missing(val):
                        continue
                    exps.setdefault(exp, {})[style] = _cell_str(val)
                if exps:
                    fam_map[fam] = exps
            families_by_lang[code] = fam_map

        return cls(
            core_by_key=core_by_key,
            separators_by_lang=separators_by_lang,
            impact_lang_by_lang=impact_lang_by_lang,
            families_by_lang=families_by_lang,
        )


class UnitFormatter:
    """
    Formats values for UI display using a loaded UnitsConfig.

    The formatter is pure (no global state) and safe to reuse across requests.
    """

    def __init__(self, config: UnitsConfig):
        self._cfg = config
        self._separator_provider: Optional[Callable[[str], Optional[Separators]]] = None

    @classmethod
    def from_excel(cls, path: str) -> "UnitFormatter":
        return cls(UnitsConfig.from_excel(path))

    def set_separator_provider(self, provider: Optional[Callable[[str], Optional[Separators]]]) -> None:
        self._separator_provider = provider

    def _seps(self, lang: str) -> Separators:
        if self._separator_provider is not None:
            try:
                provided = self._separator_provider(lang)
                if isinstance(provided, Separators):
                    return provided
                if isinstance(provided, dict):
                    return Separators(
                        thousand=str(provided.get("thousand") or ""),
                        decimal=str(provided.get("decimal") or "."),
                    )
            except Exception:
                pass
        code = _norm_lang(lang)
        return self._cfg.separators_by_lang.get(code) or self._cfg.separators_by_lang["en"]

    def _lang_row(self, impact_key: str, lang: str) -> ImpactLangRow:
        code = _norm_lang(lang)
        m = self._cfg.impact_lang_by_lang.get(code) or {}
        row = m.get(impact_key)
        if row:
            return row
        # Default empty mapping.
        return ImpactLangRow(impact_key=impact_key, family_key="", base_short="", base_long="", suffix_short="", suffix_long="")

    def _family_labels(self, family_key: str, lang: str) -> Dict[int, Dict[str, str]]:
        code = _norm_lang(lang)
        return (self._cfg.families_by_lang.get(code) or {}).get(family_key, {})

    @staticmethod
    def _pick_label(labels: Dict[str, str], style: LabelStyle) -> str:
        want = labels.get(style) or ""
        if want.strip():
            return want.strip()
        other = labels.get("long" if style == "short" else "short") or ""
        return other.strip()

    @staticmethod
    def _choose_exponent(
        *,
        abs_value_base: float,
        allowed_exponents: list[int],
        min_display: float,
        max_display: float,
        scale_mode: str,
        default_exponent: Optional[int],
    ) -> int:
        exps = sorted(set(int(e) for e in allowed_exponents))
        if not exps:
            return 0

        def disp(exp: int) -> float:
            return abs_value_base / (10.0 ** exp)

        if scale_mode == "fixed":
            if default_exponent is not None and default_exponent in exps:
                return int(default_exponent)
            if default_exponent is not None:
                # Closest available exponent (by absolute difference).
                return min(exps, key=lambda e: abs(e - int(default_exponent)))
            return 0 if 0 in exps else exps[0]

        # auto mode
        if abs_value_base == 0.0:
            if default_exponent is not None and default_exponent in exps:
                return int(default_exponent)
            return 0 if 0 in exps else exps[0]

        ok = [e for e in exps if min_display <= disp(e) < max_display]
        if ok:
            return max(ok)

        d_min = disp(min(exps))
        d_max = disp(max(exps))
        if d_min < min_display:
            # Even the least divisor yields too small a number: choose smallest exponent (largest display).
            return min(exps)
        if d_max >= max_display:
            # Even the biggest divisor yields too big a number: choose largest exponent (smallest display).
            return max(exps)

        # Gap case: pick exponent that gets closest to the target interval.
        def penalty(e: int) -> float:
            d = disp(e)
            if d < min_display:
                return math.log(min_display / max(d, 1e-300))
            if d >= max_display:
                return math.log(max(d, 1e-300) / max_display)
            return 0.0

        return min(exps, key=penalty)

    def format_value(
        self,
        impact_key: str,
        value_source: float,
        lang: str,
        *,
        style: LabelStyle = "short",
    ) -> Dict[str, Any]:
        """
        Format a value for UI display.

        Returns a dict with:
            value_base, value_display, value_display_formatted,
            unit_short, unit_long, chosen_exponent, chosen_factor
        """
        if impact_key not in self._cfg.core_by_key:
            raise UnitsConfigError(f"Unknown impact_key: {impact_key}")

        core = self._cfg.core_by_key[impact_key]
        try:
            value_base = float(value_source) * float(core.source_to_base or 1.0)
        except Exception:
            value_base = 0.0

        lang_row = self._lang_row(impact_key, lang)
        family_key = (lang_row.family_key or "").strip()

        seps = self._seps(lang)

        # Default output (fixed/fallback)
        chosen_exponent = 0
        chosen_factor = 1.0
        value_display = value_base
        unit_short = (lang_row.base_short or "").strip()
        unit_long = (lang_row.base_long or "").strip()

        # If family missing or unknown => fixed using base labels, else base_unit.
        fam_labels = self._family_labels(family_key, lang) if family_key else {}
        if not family_key or not fam_labels:
            if not unit_short:
                unit_short = core.base_unit
            if not unit_long:
                unit_long = unit_short
        else:
            allowed = sorted(fam_labels.keys())
            chosen_exponent = self._choose_exponent(
                abs_value_base=abs(value_base),
                allowed_exponents=allowed,
                min_display=float(core.min_display),
                max_display=float(core.max_display),
                scale_mode=str(core.scale_mode),
                default_exponent=core.default_exponent,
            )
            chosen_factor = float(10.0 ** int(chosen_exponent))
            value_display = value_base / chosen_factor if chosen_factor else value_base

            # Build family label with fallbacks between styles.
            labels = fam_labels.get(int(chosen_exponent), {})
            fam_short = self._pick_label(labels, "short")
            fam_long = self._pick_label(labels, "long")
            if not fam_short and not fam_long:
                # Missing exponent labels: fallback to base unit.
                fam_short = core.base_unit
                fam_long = fam_short
            elif not fam_short:
                fam_short = fam_long
            elif not fam_long:
                fam_long = fam_short

            # Apply suffixes.
            suf_short = (lang_row.suffix_short or "").strip()
            suf_long = (lang_row.suffix_long or "").strip()
            unit_short = f"{fam_short} {suf_short}".strip() if suf_short else fam_short
            unit_long = f"{fam_long} {suf_long}".strip() if suf_long else fam_long

        # Round + format for display.
        try:
            value_display_rounded = round(float(value_display), int(core.decimals))
        except Exception:
            value_display_rounded = float(value_display) if isinstance(value_display, (int, float)) else 0.0

        formatted = _format_number(
            value_display_rounded,
            decimals=int(core.decimals),
            thousand_sep=seps.thousand,
            decimal_sep=seps.decimal,
        )

        return {
            "value_base": float(value_base),
            "value_display": float(value_display_rounded),
            "value_display_formatted": formatted,
            "unit_short": str(unit_short),
            "unit_long": str(unit_long),
            "chosen_exponent": int(chosen_exponent),
            "chosen_factor": float(chosen_factor),
        }

    def format_value_tuple(
        self,
        impact_key: str,
        value_source: float,
        lang: str,
        *,
        style: LabelStyle = "short",
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Convenience wrapper:
            returns (formatted_value, unit_label, metadata_dict)
        """
        meta = self.format_value(impact_key, value_source, lang, style=style)
        unit = meta["unit_short"] if style == "short" else meta["unit_long"]
        return meta["value_display_formatted"], unit, meta



class Index:
    """
    The Index class is responsible for managing sector, region, and impact indices 
    within the IOSystem. It provides functionalities to read and update hierarchical 
    multi-indices, load data from Excel files, and generate new Excel files for sectoral 
    and regional classifications.

    Key Responsibilities:
    - Loading sector, region, and impact data from Excel files.
    - Constructing MultiIndex structures for hierarchical data representation.
    - Updating matrix labels to ensure consistency within the IOSystem.
    - Creating new Excel files for sectoral, regional, and impact classifications.

    Attributes:
        IOSystem: The main input-output system object that stores economic and 
                  environmental data, including matrices for analysis.

    Methods:
        read_configs(): Reads sector, region, and impact data from Excel files 
                       and constructs MultiIndex structures.
        update_multiindices(): Updates all matrices within the IOSystem to use 
                               the correct hierarchical indices.
        write_configs(language=None): Generates and saves sector, region, impact, 
                                      and unit classification data into Excel files.
    """
    
    def __init__(self, iosystem):
        """
        Initializes the Index object with a reference to the IOSystem object.

        Args:
            iosystem: Reference to the IOSystem object
        """
        self.iosystem = iosystem

        # Initialize attributes that will be populated by read_configs
        self.sectors_df = None
        self.raw_materials_df = None
        self.regions_df = None
        self.exiobase_to_map_df = None
        self.population_df = None
        self.impacts_df = None
        self.impacts_exiobase_df = None
        self.impact_color_df = None
        self.units_df = None
        self.general_df = None

        self.amount_sectors = None
        self.amount_regions = None
        self.amount_impacts = None

        self.general_dict = {}
        self.impact_label_to_key: Dict[str, str] = {}
        self.impact_key_to_label: Dict[str, str] = {}
        self.raw_material_indices = []
        self.not_raw_material_indices = []
        self.languages = []
        self.unit_formatter: Optional[UnitFormatter] = None

    def read_configs(self) -> None:
        """
        Reads and processes multiple Excel files, loading data into corresponding instance variables for later use in 
        the IOSystem. The method validates the structure and content of each Excel sheet, ensuring that the data 
        meets expected formats and lengths.

        The method performs the following actions:
        - Maps each data attribute to its corresponding Excel file and sheet based on the system's language setting.
        - Reads the data from Excel files and assigns them to instance variables (e.g., `self.sectors_df`, `self.regions_df`).
        - Reverses the column order for certain DataFrames to ensure consistency in hierarchical processing.
        - Verifies that the expected number of rows in each DataFrame matches a predefined value to maintain data integrity.
        - Checks for duplicate column names in certain sheets and raises an error if found.
        - Catches and logs `FileNotFoundError` if any required Excel files are missing, and raises the exception with a clear message.
        - Validates data lengths to ensure that each DataFrame has the expected number of rows.
        - Stores unit transformation data for later use in unit calculations and creates a dictionary mapping 'exiobase' to 'translation' from the general data.

        Raises:
        - FileNotFoundError: If a required Excel file is missing.
        - ValueError: If there are any issues with duplicate columns or mismatched row lengths.

        This method ensures that all necessary data is loaded into the system and validated, allowing for reliable processing 
        in subsequent steps.
        """
        
        try:
            # Mapping of df_id to file names, sheet names, and expected lengths
            # Expected lengths are aggregation-specific; use None to skip validation.
            file_mapping = {
                "sectors_df": ("sectors.xlsx", self.iosystem.language, None),
                "raw_materials_df": ("standards.xlsx", "raw_material", None),
                "regions_df": ("regions.xlsx", self.iosystem.language, None),
                "exiobase_to_map_df": ("standards.xlsx", "map", None),
                "impacts_df": ("impacts.xlsx", self.iosystem.language, None),
                # Canonical EXIOBASE impact keys, used to map translated labels -> impact_key
                "impacts_exiobase_df": ("impacts.xlsx", "Exiobase", None),
                "impact_color_df": ("standards.xlsx", "impact_color", None),
                # NOTE: `units.xlsx` was redesigned to hold display scaling + i18n labels (new schema).
                # The legacy UI parts (SupplyChain.transform_unit, etc.) still expect the old per-language
                # unit transformation table (impact label -> divisor/decimals/unit).
                #
                # Therefore we read the legacy transformation table from `units_legacy.xlsx` and load the
                # new schema separately via `load_unit_display_config()`.
                # units_legacy.xlsx is optional: falls back to legacy_config_dir (config2/) if not in
                # the aggregation folder.
                "units_df": ("units_legacy.xlsx", self.iosystem.language, None),
            }
            optional_df_ids = {"units_df"}

            # Attempt to load each Excel file and assign it to the corresponding attribute
            for df_id, (file_name, sheet_name, expected_length) in file_mapping.items():
                try:
                    # Search order: fast DB → new aggregation dir → legacy config dir (config2).
                    # We iterate through ALL candidates until one successfully provides the
                    # requested sheet — so a file that exists but lacks the sheet still falls
                    # through to the next candidate.
                    legacy_dir = getattr(self.iosystem, 'legacy_config_dir', None)
                    if file_name == "standards.xlsx":
                        candidates = [
                            os.path.join(self.iosystem.current_fast_database_path, file_name),
                            getattr(self.iosystem, "standards_config_path", ""),
                        ]
                    elif df_id == "impacts_exiobase_df":
                        candidates = [
                            os.path.join(self.iosystem.current_fast_database_path, file_name),
                            os.path.join(self.iosystem.excel_config_dir, file_name),
                            os.path.join(os.path.dirname(getattr(self.iosystem, "exiobase_regions_path", "")), "impacts.xlsx"),
                        ]
                    elif df_id == "units_df":
                        candidates = [
                            os.path.join(self.iosystem.current_fast_database_path, file_name),
                            os.path.join(self.iosystem.excel_config_dir, file_name),
                            os.path.join(os.path.dirname(getattr(self.iosystem, "exiobase_regions_path", "")), file_name),
                        ]
                    else:
                        candidates = [
                            os.path.join(self.iosystem.current_fast_database_path, file_name),
                            os.path.join(self.iosystem.excel_config_dir, file_name),
                        ]
                    if legacy_dir:
                        candidates.append(os.path.join(legacy_dir, file_name))

                    df = None
                    last_error = None
                    for candidate in candidates:
                        if not os.path.exists(candidate):
                            continue
                        try:
                            df = pd.read_excel(candidate, sheet_name=sheet_name)
                            break
                        except Exception as e:
                            last_error = e
                            continue

                    if df is None:
                        if df_id in optional_df_ids:
                            setattr(self, df_id, None)
                            logging.debug(f"Optional config missing: {file_name}/{sheet_name}")
                            continue
                        if last_error is not None:
                            raise last_error
                        raise FileNotFoundError(f"Could not find '{file_name}' in any config directory")
                    amount = len(df)

                    # For sectors/regions: reverse for hierarchical UI processing.
                    # For impacts: keep the display label in column 0 so the selected impact
                    # still matches `.loc[impact]` on the impact matrices after aggregation changes.
                    if df_id in ['sectors_df', 'regions_df', 'impacts_df']:
                        if df_id == 'impacts_df':
                            ordered_cols = [
                                col for col in ("impact_label", "category_label", "impact_key")
                                if col in df.columns
                            ]
                            remaining_cols = [col for col in df.columns if col not in ordered_cols]
                            if ordered_cols:
                                df = df.loc[:, ordered_cols + remaining_cols]
                            else:
                                df = df.iloc[:, ::-1]
                        else:
                            # Reverse column order for consistent hierarchical processing
                            df = df.iloc[:, ::-1]

                        # Store the number of rows as reference
                        setattr(self, f"amount_{df_id[:-3]}", amount)

                        # Check for unique column names
                        duplicate_columns = df.columns[df.columns.duplicated()]
                        if len(duplicate_columns) > 0:
                            raise ValueError(
                                f"Sheet '{sheet_name}' in '{file_name}' contains duplicate column names: "
                                f"{', '.join(duplicate_columns)}"
                            )

                    # Verify length (only when an explicit expected length is given)
                    if expected_length is not None and amount != expected_length:
                        raise ValueError(
                            f"Expected {expected_length} rows in sheet '{sheet_name}' of '{file_name}', "
                            f"but found {amount}"
                        )

                    # Set the DataFrame as an instance variable
                    setattr(self, df_id, df)
                    logging.debug(f"Successfully loaded: {file_name}/{sheet_name} ({amount} rows)")

                except Exception as e:
                    logging.error(f"Error loading {file_name}/{sheet_name}: {e}")
                    raise

            # Store unit transformations for later use in unit calculations
            if self.units_df is not None:
                self.iosystem.index.unit_transform = self.units_df.values.tolist()

            # Load general_dict from JSON translation file (replaces general.xlsx)
            self._load_general_dict_from_json()

            # Build impact label <-> impact_key mapping (row-order alignment in impacts.xlsx)
            try:
                if (
                    self.impacts_df is not None
                    and self.impacts_exiobase_df is not None
                    and len(self.impacts_df) == len(self.impacts_exiobase_df)
                ):
                    labels = [str(x).strip() for x in self.impacts_df.iloc[:, 0].tolist()]
                    key_series = (
                        self.impacts_exiobase_df["impact_key"]
                        if "impact_key" in self.impacts_exiobase_df.columns
                        else self.impacts_exiobase_df.iloc[:, 0]
                    )
                    keys = [str(x).strip() for x in key_series.tolist()]
                    self.impact_label_to_key = {
                        lab: key for lab, key in zip(labels, keys) if lab and key and lab.lower() != "nan"
                    }
                    self.impact_key_to_label = {
                        key: lab for lab, key in zip(labels, keys) if lab and key and key.lower() != "nan"
                    }
            except Exception:
                self.impact_label_to_key = {}
                self.impact_key_to_label = {}

            # Optional: load unit display scaling config (new units.xlsx structure)
            self.load_unit_display_config()

            # Optional: population data for per-capita metrics in maps/tooltips
            self._read_population_sheet()

            # Create list of all raw material indices
            self._create_raw_material_indices()

            # Determine available languages
            self._determine_available_languages()

            logging.debug("Configuration files successfully read")

        except Exception as e:
            logging.error(f"Error during Excel reading and processing: {e}")
            raise

    def load_unit_display_config(self, units_xlsx_path: Optional[str] = None) -> None:
        """
        Best-effort: load unit display scaling + i18n config from `units.xlsx`.

        This does not affect internal computations; it only provides a formatter
        to scale units and format numbers for UI display.
        """
        candidates = []
        if units_xlsx_path:
            candidates.append(units_xlsx_path)
        candidates.extend(
            [
                os.path.join(self.iosystem.current_fast_database_path, "units.xlsx"),
                os.path.join(self.iosystem.excel_config_dir, "units.xlsx"),
                os.path.join(os.path.dirname(getattr(self.iosystem, "exiobase_regions_path", "")), "units.xlsx"),
                os.path.join(getattr(self.iosystem, "legacy_config_dir", ""), "units.xlsx"),
            ]
        )

        for p in candidates:
            if not p or not os.path.exists(p):
                continue
            try:
                self.unit_formatter = UnitFormatter.from_excel(p)
                self.unit_formatter.set_separator_provider(self._translation_number_separators)
                logging.debug(f"Loaded unit display config: {p}")
                return
            except UnitsConfigError as e:
                # If file exists but doesn't match new schema, keep going.
                logging.debug(f"units.xlsx at '{p}' is not in the new schema: {e}")
            except Exception as e:
                logging.debug(f"Failed to load unit display config from '{p}': {e}")

        self.unit_formatter = None

    def _translation_number_separators(self, lang: Optional[str] = None) -> Separators:
        """
        Read number separators from the active translation JSON/general_dict.
        """
        code = _norm_lang(lang or getattr(self.iosystem, "language", "en"))
        thousand = str(
            self.general_dict.get("number_thousand_separator")
            or self.general_dict.get("thousand_separator")
            or ""
        )
        decimal = str(
            self.general_dict.get("number_decimal_separator")
            or self.general_dict.get("decimal_separator")
            or "."
        )
        if code == "de":
            return Separators(thousand=thousand or ".", decimal=decimal or ",")
        if code == "fr":
            return Separators(thousand=thousand or " ", decimal=decimal or ",")
        if code == "es":
            return Separators(thousand=thousand or ".", decimal=decimal or ",")
        return Separators(thousand=thousand or ",", decimal=decimal or ".")

    def format_number_localized(
        self,
        value: float,
        *,
        decimals: int = 2,
        lang: Optional[str] = None,
    ) -> str:
        """
        Format a plain numeric value using the active translation-defined separators.
        """
        seps = self._translation_number_separators(lang)
        return _format_number(
            float(value),
            decimals=max(0, int(decimals)),
            thousand_sep=seps.thousand,
            decimal_sep=seps.decimal,
        )

    def format_value_display(
        self,
        impact_key: str,
        value_source: float,
        *,
        lang: Optional[str] = None,
        style: str = "short",
    ) -> Tuple[str, str, Dict[str, Union[str, float, int]]]:
        """
        Format a numeric value for UI display using the optional unit display config.

        Returns:
            (formatted_value, unit_label, metadata)

        Raises:
            ValueError if the unit display formatter is not available.
        """
        if self.unit_formatter is None:
            raise ValueError("Unit display config not loaded (units.xlsx new schema missing).")
        language = lang or getattr(self.iosystem, "language", "en")
        return self.unit_formatter.format_value_tuple(impact_key, value_source, language, style=style)  # type: ignore[arg-type]

    def impact_key_from_label(self, impact: str) -> str:
        """
        Map a localized impact label (e.g. 'Wertschöpfung') to the canonical EXIOBASE impact_key
        (e.g. 'Value Added'). If no mapping is available, returns the input unchanged.
        """
        s = (impact or "").strip()
        if not s:
            return s
        return self.impact_label_to_key.get(s, s)

    def _create_raw_material_indices(self) -> None:
        """
        Creates lists of raw material and non-raw material indices.
        """
        # Create base indices
        raw_material_base = self.raw_materials_df[
            self.raw_materials_df['raw_material'] == True
        ].index.tolist()

        not_raw_material_base = self.raw_materials_df[
            self.raw_materials_df['raw_material'] == False
        ].index.tolist()

        # Create expanded indices for all regions
        self.raw_material_indices = []
        self.not_raw_material_indices = []

        num_regions = int(getattr(self, "amount_regions", len(self.regions_df)))
        num_sectors = int(getattr(self, "amount_sectors", len(self.sectors_df)))

        for region in range(num_regions):
            offset = region * num_sectors
            self.raw_material_indices.extend([offset + idx for idx in raw_material_base])
            self.not_raw_material_indices.extend([offset + idx for idx in not_raw_material_base])

    def _load_general_dict_from_json(self) -> None:
        """
        Loads general_dict (UI label translations) from config/translations/<language>.json.
        Falls back to general.xlsx if the JSON file is not found.
        """
        import json as _json

        translations_dir = getattr(self.iosystem, 'translations_dir', None)
        lang = self.iosystem.language
        json_path = os.path.join(translations_dir, f"{lang}.json") if translations_dir else None

        if json_path and os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.general_dict = _json.load(f)
                logging.debug(f"Loaded general_dict from {json_path}")
                return
            except Exception as e:
                logging.warning(f"Could not load translation JSON '{json_path}': {e}")

        # Fallback: try general.xlsx (legacy config2 format)
        for base in [self.iosystem.current_fast_database_path,
                     getattr(self.iosystem, 'legacy_config_dir', None)]:
            if not base:
                continue
            xlsx_path = os.path.join(base, "general.xlsx")
            if os.path.exists(xlsx_path):
                try:
                    df = pd.read_excel(xlsx_path, sheet_name=lang)
                    self.general_dict = dict(zip(df['exiobase'], df['translation']))
                    logging.debug(f"Loaded general_dict from {xlsx_path}")
                    return
                except Exception as e:
                    logging.warning(f"Could not load general.xlsx from '{xlsx_path}': {e}")

        logging.warning(f"No translation source found for language '{lang}', general_dict will be empty")
        self.general_dict = {}

    def _determine_available_languages(self) -> None:
        """
        Determines available languages from config/translations/*.json files.
        Falls back to general.xlsx sheet names if the translations directory is not available.
        """
        translations_dir = getattr(self.iosystem, 'translations_dir', None)
        if translations_dir and os.path.exists(translations_dir):
            try:
                self.languages = sorted([
                    os.path.splitext(f)[0]
                    for f in os.listdir(translations_dir)
                    if f.endswith('.json')
                ])
                return
            except Exception as e:
                logging.warning(f"Could not read translations directory: {e}")

        # Fallback: read sheet names from general.xlsx
        try:
            file_path = os.path.join(self.iosystem.current_fast_database_path, "general.xlsx")
            with pd.ExcelFile(file_path) as xls:
                self.languages = xls.sheet_names
        except FileNotFoundError:
            logging.warning("Could not find 'general.xlsx' to determine available languages")
            self.languages = []

    def _read_population_sheet(self) -> None:
        """
        Best-effort loading of a 'population' sheet from regions.xlsx.

        The sheet is optional. If present, it should contain at least:
          - a region code column (preferably EXIOBASE codes like 'AT', 'DE', ...)
          - a numeric population column

        The loader tries the year-specific fast database first, then falls back to config/regions.xlsx.
        """
        self.population_df = None
        candidates = [
            os.path.join(self.iosystem.current_fast_database_path, "standards.xlsx"),
            getattr(self.iosystem, "standards_config_path", ""),
            os.path.join(self.iosystem.current_fast_database_path, "regions.xlsx"),
            os.path.join(self.iosystem.excel_config_dir, "regions.xlsx"),
            os.path.join(getattr(self.iosystem, "legacy_config_dir", ""), "regions.xlsx"),
        ]
        for path in candidates:
            if not os.path.exists(path):
                continue
            try:
                with pd.ExcelFile(path) as xls:
                    sheet = next((s for s in xls.sheet_names if str(s).strip().lower() == "population"), None)
                if not sheet:
                    continue
                df = pd.read_excel(path, sheet_name=sheet)
                if df is None or getattr(df, "empty", True):
                    continue
                self.population_df = df
                logging.debug(f"Loaded population sheet from: {path}")
                return
            except Exception:
                continue

    def _population_by_exiobase(self) -> Dict[str, float]:
        """
        Parse the optional population_df into a mapping: EXIOBASE code -> population.
        """
        df = self.population_df
        if df is None or getattr(df, "empty", True):
            return {}

        cols = [str(c).strip().lower() for c in df.columns.tolist()]
        if not cols:
            return {}

        code_col = 0
        for i, c in enumerate(cols):
            if "exiobase" in c or c in {"code", "region", "country"}:
                code_col = i
                break

        pop_col = None
        for i, c in enumerate(cols):
            if "population" in c or "einwohner" in c:
                pop_col = i
                break
        if pop_col is None:
            pop_col = 1 if df.shape[1] >= 2 else None
        if pop_col is None:
            return {}

        codes = df.iloc[:, code_col].astype(str).str.strip()
        pops = pd.to_numeric(df.iloc[:, pop_col], errors="coerce")

        out: Dict[str, float] = {}
        for code, pop in zip(codes.tolist(), pops.tolist()):
            c = str(code or "").strip()
            if not c or c.lower() == "nan":
                continue
            try:
                p = float(pop)
            except Exception:
                continue
            if not np.isfinite(p) or p <= 0:
                continue
            out[c] = p
        return out

    def create_multiindices(self) -> None:
        """
        Creates MultiIndex structures for sector, region, and impact matrices in the IOSystem. This method
        generates hierarchical indices to manage the relationships between sectors, regions, and impacts. 

        The method performs the following actions:
        - Expands the `sectors_df` DataFrame to match the number of regions, ensuring each sector exists for each region.
        - Matches regions to sectors by repeating the region indices to align with the number of sectors.

        The method generates the following MultiIndices:
        - `self.sector_multiindex`: A hierarchical MultiIndex for sectors and regions, forming a hierarchical index based on region and sector data.
        - `self.impact_multiindex`: A hierarchical MultiIndex for impacts, allowing for easy reference of impact categories in the system.
        - `self.region_multiindex`: A region-specific MultiIndex, useful for region-based indexing.
        - `self.sector_multiindex_per_region`: A sector-specific MultiIndex for a single region, allowing for region-specific sectoral analysis.

        The MultiIndex structures are used for efficiently referencing and indexing sector-based and impact-based data 
        in matrices, enabling the system to handle complex, multi-dimensional relationships between regions, sectors, 
        and impacts.
        """

        # Expand sectors to match all regions
        self.matching_sectors_df = pd.concat([self.sectors_df] * self.amount_regions, ignore_index=True)

        # Match regions to sectors
        self.matching_regions_df = self.regions_df.loc[
            np.repeat(self.regions_df.index, self.amount_sectors)
        ].reset_index(drop=True)

        # Create MultiIndex for sectors and regions
        self.sector_multiindex = pd.MultiIndex.from_arrays(
            [self.matching_regions_df[col] for col in self.matching_regions_df.columns] +
            [self.matching_sectors_df[col] for col in self.matching_sectors_df.columns],
            names=(self.matching_regions_df.columns.tolist() +
                   self.matching_sectors_df.columns.tolist())
        )

        # Create MultiIndex for impacts
        self.impact_multiindex = pd.MultiIndex.from_arrays(
            [self.impacts_df[col] for col in self.impacts_df.columns],
            names=self.impacts_df.columns.tolist()
        )

        # Create MultiIndex only for regions
        self.region_multiindex = pd.MultiIndex.from_arrays(
            [self.regions_df[col] for col in self.regions_df.columns],
            names=self.regions_df.columns.tolist()
        )

        # Create MultiIndex for sectors per region
        self.sector_multiindex_per_region = pd.MultiIndex.from_arrays(
            [self.sectors_df[col] for col in self.sectors_df.columns],
            names=self.sectors_df.columns.tolist()
        )

        # Create MultiIndex for impact per region
        self.impact_per_region_multiindex = pd.MultiIndex.from_tuples(
            [imp + reg for imp, reg in itertools.product(self.impact_multiindex, self.region_multiindex)],
            names=list(self.impact_multiindex.names) + list(self.region_multiindex.names)
        )

        logging.debug("MultiIndices successfully created")

    def update_multiindices(self) -> None:
        """
        Updates the MultiIndex structures for sector and impact matrices in the IOSystem. This method loads the
        latest Excel data, creates and updates MultiIndex structures for key matrices (A, L, Y, I), impact matrices 
        (S, total, retail, etc.), and regional matrices if available. It also extracts unique sector, region, 
        and impact names for system-wide reference and updates the impact units DataFrame.

        The method performs the following actions:
        - Loads the latest sector, region, and impact data from Excel files.
        - Creates or updates the MultiIndex structures for sector-based matrices (A, L, Y, I).
        - Updates the MultiIndex for impact matrices (S, total, retail, etc.), ensuring correct labeling.
        - If regional matrices exist, updates them with appropriate region-based MultiIndexes.
        - Extracts unique names for sectors, regions, impacts, and units to be used throughout the system.
        - Updates the `regions_exiobase` list from the "regions.xlsx" file.
        - Updates the impact unit DataFrame, ensuring each impact has its corresponding unit.

        The method relies on the `self.sectors_df`, `self.regions_df`, `self.impacts_df`, and other class attributes 
        to manage the data. It is intended to ensure that all matrices in the IOSystem are correctly indexed and 
        labeled for further analysis.
        """

        # Load the latest config data and update sector and impact multiindices
        self.read_configs()
        self.create_multiindices()

        # Extract unique names for system-wide reference
        # Use the finest level (last col after reversal) for sectors/regions — needed for
        # matrix index calculation (row = region*num_sectors + sector).
        self.iosystem.sectors = self.sectors_df.iloc[:, -1].unique().tolist()
        self.iosystem.regions = self.regions_df.iloc[:, -1].unique().tolist()
        # For impacts: use level 0 (first col after reversal = outermost MultiIndex level).
        # This ensures .loc[impact] on the impact matrices matches what iosystem.impacts lists.
        # For single-column sheets (config2) iloc[:,0] == iloc[:,-1] → backward-compatible.
        self.iosystem.impacts = self.impacts_df.iloc[:, 0].tolist()
        if self.units_df is not None:
            self.iosystem.units = self.units_df.iloc[:, -1].tolist()

        # Load 'regions_exiobase' data (fast db first, fallback to config)
        regions_xlsx_candidates = [
            os.path.join(self.iosystem.current_fast_database_path, "standards.xlsx"),
            os.path.join(self.iosystem.current_fast_database_path, "regions.xlsx"),
            getattr(self.iosystem, "exiobase_regions_path", ""),
            os.path.join(self.iosystem.excel_config_dir, "regions.xlsx"),
            os.path.join(getattr(self.iosystem, "legacy_config_dir", ""), "regions.xlsx"),
        ]
        regions_exiobase = None
        for p in regions_xlsx_candidates:
            if not os.path.exists(p):
                continue
            try:
                if os.path.basename(p).lower() == "standards.xlsx":
                    df = pd.read_excel(p, sheet_name="population")
                    regions_exiobase = df.iloc[:, 0].astype(str).str.strip().tolist()
                else:
                    df = pd.read_excel(p, sheet_name="Exiobase")
                    regions_exiobase = df.iloc[:, -1].astype(str).str.strip().tolist()
                if regions_exiobase:
                    break
            except Exception:
                continue
        self.iosystem.regions_exiobase = regions_exiobase or []

        # Optional population mapping for per-capita tooltips/maps
        try:
            self.iosystem.population_by_exiobase = self._population_by_exiobase()
        except Exception:
            self.iosystem.population_by_exiobase = {}

        # Update impact units DataFrame
        impact_units = list(self.iosystem.units or [])
        if len(impact_units) != len(self.iosystem.impacts):
            impact_units = (impact_units + [""] * len(self.iosystem.impacts))[:len(self.iosystem.impacts)]
        self.iosystem.impact.unit = pd.DataFrame({"unit": impact_units}, index=self.iosystem.impacts)

        # Define matrix mappings
        matrix_mappings = {
            "standard_matrices": ["A", "L", "Y", "I"],
            "impact_matrices": ["S", "D_cba"],
            "regional_impact_matrices": ["total", "retail", "direct_suppliers",
                                        "resource_extraction", "preliminary_products"],
            "regional_matrices": ["retail_regional", "direct_suppliers_regional",
                                 "resource_extraction_regional", "preliminary_products_regional"]
        }

        # Update matrix indices
        self._update_matrix_indices(matrix_mappings)

        # Store classification structures
        self.sector_classification = self.sectors_df.columns.tolist()
        self.region_classification = self.regions_df.columns.tolist()
        self.impact_classification = self.impacts_df.columns.tolist()

        # Update the map
        self.update_map()

        logging.debug("MultiIndices successfully updated")

    def _update_matrix_indices(self, matrix_mappings: Dict[str, List[str]]) -> None:
        """
        Updates indices for different matrix groups.
        """
        for matrix_group, matrices in matrix_mappings.items():
            if matrix_group == "standard_matrices":
                for matrix_name in matrices:
                    if hasattr(self.iosystem, matrix_name):
                        matrix_data = getattr(self.iosystem, matrix_name)
                        if getattr(matrix_data, "shape", (0, 0))[0] == len(self.sector_multiindex):
                            matrix_data.index = self.sector_multiindex
                        if getattr(matrix_data, "shape", (0, 0))[1] == len(self.sector_multiindex):
                            matrix_data.columns = self.sector_multiindex

            elif matrix_group == "impact_matrices":
                for matrix_name in matrices:
                    if hasattr(self.iosystem.impact, matrix_name):
                        impact_matrix = getattr(self.iosystem.impact, matrix_name)
                        impact_matrix.index = self.impact_multiindex
                        impact_matrix.columns = self.sector_multiindex

            elif matrix_group == "regional_impact_matrices":
                for matrix_name in matrices:
                    if hasattr(self.iosystem.impact, matrix_name):
                        impact_matrix = getattr(self.iosystem.impact, matrix_name)
                        impact_matrix.index = self.impact_per_region_multiindex
                        impact_matrix.columns = self.sector_multiindex

            elif (matrix_group == "regional_matrices" and
                  self.iosystem.impact.region_indices is not None):
                for matrix_name in matrices:
                    if hasattr(self.iosystem.impact, matrix_name):
                        regional_matrix = getattr(self.iosystem.impact, matrix_name)
                        regional_matrix.index = self.impact_multiindex
                        regional_matrix.columns = self.sector_multiindex

    def copy_configs(self, new: bool = False, output: bool = True) -> None:
        """
        Copies configuration files from the /config folder to the fast load database.

        Args:
            new: Indicates whether new configuration (not used)
            output: Whether to display logging output
        """
        if output:
            logging.info("Copying config files from /config to the fast load database...")

        # Files from the aggregation dir. units_legacy.xlsx and general.xlsx are optional
        # (legacy config2 only) — skip silently if absent in the new config structure.
        config_files = ["sectors.xlsx", "regions.xlsx", "impacts.xlsx", "units.xlsx", "units_legacy.xlsx", "standards.xlsx"]
        optional_files = {"units_legacy.xlsx", "general.xlsx"}

        # Build a search list: new aggregation dir first, then legacy config2 as fallback
        search_dirs = [self.iosystem.excel_config_dir]
        legacy_dir = getattr(self.iosystem, 'legacy_config_dir', None)
        if legacy_dir:
            search_dirs.append(legacy_dir)

        for file_name in config_files:
            target_file = os.path.join(self.iosystem.current_fast_database_path, file_name)
            source_file = None
            if file_name == "standards.xlsx":
                candidate = getattr(self.iosystem, "standards_config_path", "")
                if candidate and os.path.exists(candidate):
                    source_file = candidate
            elif file_name == "units.xlsx":
                candidates = [
                    os.path.join(self.iosystem.excel_config_dir, file_name),
                    os.path.join(os.path.dirname(getattr(self.iosystem, "exiobase_regions_path", "")), file_name),
                ]
                for candidate in candidates:
                    if candidate and os.path.exists(candidate):
                        source_file = candidate
                        break
            elif file_name == "units_legacy.xlsx":
                candidates = [
                    os.path.join(self.iosystem.excel_config_dir, file_name),
                    os.path.join(os.path.dirname(getattr(self.iosystem, "exiobase_regions_path", "")), file_name),
                ]
                for candidate in candidates:
                    if candidate and os.path.exists(candidate):
                        source_file = candidate
                        break
            else:
                for d in search_dirs:
                    candidate = os.path.join(d, file_name)
                    if os.path.exists(candidate):
                        source_file = candidate
                        break

            if source_file:
                try:
                    shutil.copy(source_file, target_file)
                    if output:
                        logging.info(f"File {file_name} has been successfully copied")
                except Exception as e:
                    logging.error(f"Error copying {file_name}: {e}")
            elif file_name not in optional_files:
                logging.error(f"File {file_name} not found in {search_dirs}")

        self.read_configs()

    def write_configs(self, sheet_name: str) -> None:
        """
        Creates or updates Excel files for various datasets (sectors, regions, impacts, etc.) based on the provided 
        or default sheet name. This function will write the data to corresponding Excel files, either creating new ones 
        or appending to existing files. It handles special cases for certain sheets (e.g., 'exiobase') and allows 
        for the creation of sheets with custom names.

        Parameters:
        - sheet_name (str, optional): The name of the sheet to be used for writing the data. If None, 
        the default sheet name is determined by the system's language setting.

        The following files are processed:
        - "sectors.xlsx", "regions.xlsx", "impacts.xlsx", "units.xlsx", "general.xlsx"
        - Additional sheets are written as needed (e.g., "map", "color").

        The method handles the following:
        - Creates DataFrames for sectors, regions, impacts, and related data (units, general info).
        - Writes these DataFrames to the corresponding Excel sheets.
        - Ensures the Excel files are properly updated or created.
        - Provides error handling for common issues, including permission errors when opening files.

        Raises:
        - PermissionError: If any Excel file is open during the write process.
        - Exception: If any unexpected error occurs during the execution of the method.
        """

        # File paths and corresponding DataFrames
        file_data = {
            "sectors.xlsx": [(self.sectors_df.iloc[:, ::-1], sheet_name),
                            (self.raw_materials_df, "raw_material")],
            "regions.xlsx": [(self.regions_df.iloc[:, ::-1], sheet_name),
                            (self.exiobase_to_map_df, "map")],
            "impacts.xlsx": [(self.impacts_df.iloc[:, ::-1], sheet_name),
                            (self.impact_color_df, "color")],
            "units.xlsx": [(self.units_df, sheet_name)],
            "general.xlsx": [(self.general_df, sheet_name)]
        }

        # Write to Excel files
        try:
            for file_name, sheets in file_data.items():
                file_path = os.path.join(self.iosystem.current_fast_database_path, file_name)
                mode = "a" if os.path.exists(file_path) else "w"

                with pd.ExcelWriter(file_path, engine="openpyxl", mode=mode) as writer:
                    for df, sheet in sheets:
                        try:
                            df.to_excel(writer, sheet_name=sheet, index=False)
                        except Exception as e:
                            logging.error(f"Error writing to sheet '{sheet}' "
                                        f"in file '{file_name}': {e}")

            logging.info("Excel files have been successfully created or updated")
        except PermissionError:
            raise PermissionError("Make sure to close all Excel files "
                                "before running the program")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")

    def update_map(self, force: bool = False) -> None:
        """
        Creates or updates a GeoDataFrame for world regions, mapping Exiobase regions to geographical regions 
        based on the provided or default natural earth shapefile. This method loads the shapefile, applies the region 
        mapping, and dissolves the geometries by region to create a region-based GeoDataFrame. If a GeoDataFrame 
        already exists, it can be refreshed by setting the `force` parameter to True.

        Parameters:
        - naturalearth_path (str, optional): The path to the Natural Earth shapefile for world countries. 
        If None, a default URL is used to download the shapefile. Default is "ne_110m_admin_0_countries.zip".
        - force (bool, optional): If set to True, the method will force a refresh of the `world` GeoDataFrame, 
        even if it already exists. Default is False.

        The method performs the following actions:
        - Reads the shapefile for world countries using Geopandas.
        - Maps Exiobase regions to the corresponding world regions using `exiobase_to_map_df`.
        - Adds a new column for regions based on the mapping and dissolves geometries by region to create a simplified world map.
        - Returns a copy of the resulting GeoDataFrame.
        """
        try:
            world_map_path = os.path.join(self.iosystem.data_dir, "data_world_map.zip")
            self.world = gpd.read_file(world_map_path)

            self.exiobase_to_map_dict = dict(
                zip(self.exiobase_to_map_df['NAME'], self.exiobase_to_map_df['region'])
            )

            self.world["region"] = self.world["NAME"].map(self.exiobase_to_map_dict)
            self.world = self.world[["region", "geometry"]]
            self.world = self.world.dissolve(by="region")

            logging.debug("World map successfully updated")

        except Exception as e:
            logging.error(f"Error updating map: {e}")

    def get_map(self) -> gpd.GeoDataFrame:
        """
        Returns the geopandas world map with EXIOBASE regions as indices.

        Returns:
            Copy of the world map GeoDataFrame
        """
        return self.world.copy()
