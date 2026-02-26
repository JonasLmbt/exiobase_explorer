"""
unit_display.py

Unit display scaling + i18n formatting driven by `units.xlsx`.

This module is intentionally self-contained:
- It loads the Excel configuration once into an in-memory structure.
- It formats values for UI display by converting source units to base units and
  selecting a suitable display scale (10^exponent) based on the configured rules.

Primary entry point:
    UnitFormatter.from_excel(path).format_value(...)
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any, Dict, Literal, Optional, Tuple

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

        # Resolve sheet names case-insensitively.
        by_low = {str(s).strip().casefold(): str(s) for s in sheets}
        exiobase_sheet = by_low.get("exiobase") or by_low.get("exiobase ")
        if not exiobase_sheet:
            raise UnitsConfigError("Missing required sheet 'exiobase'.")

        sep_sheet = by_low.get("separators")
        if not sep_sheet:
            raise UnitsConfigError("Missing required sheet 'separators'.")

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

        sep_df = cls._read_sheet(path, sep_sheet)
        for col in ("lang", "thousand_separator", "decimal_separator"):
            if col not in sep_df.columns:
                raise UnitsConfigError(f"Sheet 'separators' is missing column '{col}'.")
        separators_by_lang: Dict[str, Separators] = {}
        for _, r in sep_df.iterrows():
            lang = _norm_lang(str(r.get("lang") or ""))
            thousand = _cell_str(r.get("thousand_separator")) or ","
            decimal = _cell_str(r.get("decimal_separator")) or "."
            separators_by_lang[lang] = Separators(thousand=thousand, decimal=decimal)
        separators_by_lang.setdefault("en", Separators(thousand=",", decimal="."))

        # Language impact mapping sheets.
        lang_sheet_by_code = {
            "de": by_low.get("deutsch"),
            "en": by_low.get("english"),
            "fr": by_low.get("français") or by_low.get("francais"),
            "es": by_low.get("español") or by_low.get("espanol"),
        }

        impact_lang_by_lang: Dict[str, Dict[str, ImpactLangRow]] = {}
        for code, sheet in lang_sheet_by_code.items():
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
        for code, base_sheet in lang_sheet_by_code.items():
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

    @classmethod
    def from_excel(cls, path: str) -> "UnitFormatter":
        return cls(UnitsConfig.from_excel(path))

    def _seps(self, lang: str) -> Separators:
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
