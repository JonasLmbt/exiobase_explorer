import tempfile
import unittest

import pandas as pd

from src.Index import UnitFormatter


def _write_units_xlsx(path: str):
    # Minimal but complete workbook for tests.
    exiobase = pd.DataFrame(
        [
            {
                "impact_key": "mass",
                "source_unit": "kg",
                "base_unit": "kg",
                "source_to_base": 1.0,
                "scale_mode": "auto",
                "default_factor": "1e0",
                "min_display": 0.1,
                "max_display": 1000.0,
                "decimals": 2,
            },
            {
                "impact_key": "fixed",
                "source_unit": "DALY",
                "base_unit": "DALY",
                "source_to_base": 1.0,
                "scale_mode": "fixed",
                "default_factor": "1e0",
                "min_display": 0.1,
                "max_display": 1000.0,
                "decimals": 3,
            },
            {
                "impact_key": "gap",
                "source_unit": "kg",
                "base_unit": "kg",
                "source_to_base": 1.0,
                "scale_mode": "fixed",
                "default_factor": "1e9",
                "min_display": 0.1,
                "max_display": 1000.0,
                "decimals": 1,
            },
        ]
    )

    separators = pd.DataFrame(
        [
            {"lang": "de", "thousand_separator": ".", "decimal_separator": ","},
            {"lang": "en", "thousand_separator": ",", "decimal_separator": "."},
        ]
    )

    deutsch = pd.DataFrame(
        [
            {
                "impact_key": "mass",
                "family_key": "mass_kg",
                "base_short": "",
                "base_long": "",
                "suffix_short": "",
                "suffix_long": "",
            },
            {
                "impact_key": "fixed",
                "family_key": "",
                "base_short": "DALY",
                "base_long": "Disability-adjusted life years",
                "suffix_short": "",
                "suffix_long": "",
            },
            {
                "impact_key": "gap",
                "family_key": "mass_kg",
                "base_short": "",
                "base_long": "",
                "suffix_short": "CO2 eq.",
                "suffix_long": "CO2 equivalents",
            },
        ]
    )

    deutsch_families = pd.DataFrame(
        [
            {"family_key": "mass_kg", "1e0_short": "kg", "1e3_short": "t", "1e6_short": "kt"},
        ]
    )

    # Long labels intentionally missing -> should fallback to short.
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        exiobase.to_excel(w, sheet_name="exiobase", index=False)
        separators.to_excel(w, sheet_name="separators", index=False)
        deutsch.to_excel(w, sheet_name="Deutsch", index=False)
        deutsch_families.to_excel(w, sheet_name="Deutsch_families", index=False)


class UnitDisplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        self.tmp.close()
        _write_units_xlsx(self.tmp.name)
        self.fmt = UnitFormatter.from_excel(self.tmp.name)

    def tearDown(self):
        try:
            import os

            os.unlink(self.tmp.name)
        except Exception:
            pass

    def test_auto_scaling_boundaries(self):
        # 1500 kg should become 1.50 t (exponent 3) for the configured range.
        meta = self.fmt.format_value("mass", 1500.0, "de", style="short")
        self.assertEqual(meta["chosen_exponent"], 3)
        self.assertEqual(meta["unit_short"], "t")
        self.assertEqual(meta["value_display_formatted"], "1,50")

    def test_negative_values_keep_sign(self):
        meta = self.fmt.format_value("mass", -1500.0, "de", style="short")
        self.assertEqual(meta["chosen_exponent"], 3)
        self.assertTrue(meta["value_display"] < 0)
        self.assertEqual(meta["value_display_formatted"], "-1,50")

    def test_zero_value_uses_default(self):
        meta = self.fmt.format_value("mass", 0.0, "de", style="short")
        self.assertEqual(meta["chosen_exponent"], 0)
        self.assertEqual(meta["unit_short"], "kg")
        self.assertEqual(meta["value_display_formatted"], "0,00")

    def test_missing_default_exponent_falls_back(self):
        # default_factor is 1e9 which isn't available; should choose closest -> 1e6
        meta = self.fmt.format_value("gap", 1e9, "de", style="short")
        self.assertEqual(meta["chosen_exponent"], 6)
        self.assertEqual(meta["unit_short"], "kt CO2 eq.")

    def test_long_label_fallback_to_short(self):
        meta = self.fmt.format_value("mass", 1500.0, "de", style="long")
        self.assertEqual(meta["unit_long"], "t")  # long missing -> short fallback

    def test_fixed_unit_no_scaling(self):
        meta = self.fmt.format_value("fixed", 12345.0, "de", style="short")
        self.assertEqual(meta["chosen_exponent"], 0)
        self.assertEqual(meta["unit_short"], "DALY")
        self.assertEqual(meta["value_display_formatted"], "12.345,000")


if __name__ == "__main__":
    unittest.main()

