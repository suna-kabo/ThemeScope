from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.generate_dashboard import (
    EXPORT_COLUMNS, RUN_OUTPUT_FILES, _all_selected, _dashboard_snapshot,
    _theme_csv_row, _write_bounded_json, _write_run_bundle, make_source_matrix,
)


class RunBundleTests(unittest.TestCase):
    def test_python_csv_exports_use_explicit_percent_and_percentage_point_units(self) -> None:
        metric = lambda value: {"status": "valid", "value": value}
        row = _theme_csv_row({
            "id": "theme", "name": "Theme", "level": "Theme", "return21": 0.1075,
            "return1m_pct": 10.75, "returns": {"5": metric(0.05), "21": metric(0.1075), "63": metric(0.2)},
            "excess_returns": {"5": metric(0.0125), "21": metric(0.025), "63": metric(-0.01)},
        })
        self.assertAlmostEqual(row["return21_pct"], 10.75)
        self.assertAlmostEqual(row["excess5_pp"], 1.25)
        self.assertNotIn("return21", row)
        self.assertNotIn("return1m_pct", row)
        self.assertNotIn("excess21", row)

        stock = {"ticker": "AAA", "returns": {"5": metric(0.1075), "21": metric(0.1075), "63": metric(0.2)}, "excess_returns": {"5": metric(0.0125), "21": metric(0.025), "63": metric(-0.01)}}
        exported = _all_selected({"themes": [{"name": "Theme", "id": "theme", "anchor": "ETF", "selected": [stock]}]}, 15)[0]
        self.assertAlmostEqual(exported["return5_pct"], 10.75)
        self.assertAlmostEqual(exported["excess5_pp"], 1.25)
        self.assertIn("return21_pct", EXPORT_COLUMNS)
        self.assertNotIn("return21", EXPORT_COLUMNS)

    def test_dashboard_payload_omits_large_audit_collections_but_keeps_ui_fields(self) -> None:
        payload = _dashboard_snapshot({
            "themes": [{"name": "Theme", "selected": [], "history": [1], "stock_audit": [2], "holdings_breadth": {"21": {"value": 50}}}],
            "candidate_metrics": [1], "registry_diagnostics": [2], "source_matrix": [3],
            "settings": {"watchlist_capacity": 20},
        })
        self.assertNotIn("candidate_metrics", payload)
        self.assertNotIn("registry_diagnostics", payload)
        self.assertNotIn("source_matrix", payload)
        self.assertNotIn("stock_audit", payload["themes"][0])
        self.assertIn("selected", payload["themes"][0])
        self.assertIn("holdings_breadth", payload["themes"][0])

    def test_bounded_json_rejects_output_before_writing_oversized_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            path = Path(temporary_dir) / "raw_inputs.json"
            with self.assertRaisesRegex(ValueError, "configured limit"):
                _write_bounded_json(path, {"payload": "large"}, 5, "raw_inputs.json")
            self.assertFalse(path.exists())

    def test_bundle_contains_each_run_file_but_not_itself(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            output_dir = Path(temporary_dir)
            for filename in RUN_OUTPUT_FILES:
                (output_dir / filename).write_text(filename, encoding="utf-8")

            bundle_path = _write_run_bundle(output_dir)

            with zipfile.ZipFile(bundle_path) as bundle:
                self.assertEqual(set(bundle.namelist()), set(RUN_OUTPUT_FILES))
                self.assertNotIn("run_bundle.zip", bundle.namelist())
                self.assertEqual(bundle.read("dashboard.html"), b"dashboard.html")

    def test_bundle_fails_clearly_if_a_run_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            with self.assertRaisesRegex(FileNotFoundError, "Missing run output"):
                _write_run_bundle(Path(temporary_dir))

    def test_iwm_holdings_are_not_mislabeled_as_sp500_constituents(self) -> None:
        raw = {
            "v5": {"index_universes": {
                "SPY": {"url": "https://example.test/sp500"},
                "QQQ": {"url": "https://example.test/nasdaq100"},
                "IWM": {"url": "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/latest-holdings.csv"},
            }},
            "context_holdings": {"IWM": {
                "url": "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/latest-holdings.csv",
                "as_of": "2026-10-22",
            }},
        }

        rows = make_source_matrix({}, raw, Path("."))

        iwm_universes = [row for row in rows if row["field"] == "Index constituent universe" and row["scope"] == "IWM"]
        iwm_holdings = [row for row in rows if row["field"] == "Official equity holdings" and row["scope"] == "IWM"]
        self.assertEqual(iwm_universes, [])
        self.assertEqual(len(iwm_holdings), 1)
        self.assertEqual(iwm_holdings[0]["provider"], "iShares")
        self.assertIn("practical Russell 2000 proxy", iwm_holdings[0]["method"])


if __name__ == "__main__":
    unittest.main()
