from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.generate_dashboard import (
    EXPORT_COLUMNS, RUN_OUTPUT_FILES, _all_selected, _dashboard_snapshot, _membership_review_rows, _primary_snapshot,
    _theme_csv_row, _v7_run_report, _write_bounded_json, _write_run_bundle, _rehydrate_index_universes,
    _retain_imported_index_metrics, make_source_matrix,
)


class RunBundleTests(unittest.TestCase):
    def test_run_report_counts_review_statuses_from_approved_configuration(self) -> None:
        snapshot = {
            "session_date": "2026-10-23",
            "themes": [
                {"id": "complete", "name": "Complete", "anchor": "AAA"},
                {"id": "short", "name": "Short", "anchor": "BBB"},
            ],
        }
        raw = {"watchlists": {"watchlists": [
            {"theme_id": "complete", "anchor": "AAA", "status": "complete", "members": [{"ticker": "AAA1"}]},
            {"theme_id": "short", "anchor": "BBB", "status": "reviewed_short", "members": [{"ticker": "BBB1"}]},
        ]}}
        report = _v7_run_report(snapshot, raw)
        self.assertIn("Final reviewed lists: 2/2 (complete 1; reviewed short 1; reviewed ETF-only 0)", report)

    def test_membership_review_export_preserves_approved_reasons_and_sources(self) -> None:
        rows = _membership_review_rows({"watchlists": [{
            "theme_id": "theme", "anchor": "ETF", "status": "complete", "reviewed_candidate_count": 18,
            "members": [{
                "ticker": "AAA", "company": "Alpha", "exchange": "NASDAQ", "instrument_type": "operating_company",
                "relationship": "Core", "reason": "Builds the core hardware for this theme.",
                "source_url": "https://example.com/holdings", "reason_source_url": "https://example.com/company",
                "maintenance": {"date": "2026-10-15", "source_type": "anchor_etf", "adjusted_price_sessions": 250},
            }],
        }]}, [{"id": "theme", "name": "Theme"}])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["reason"], "Builds the core hardware for this theme.")
        self.assertEqual(rows[0]["reason_source_url"], "https://example.com/company")
        self.assertEqual(rows[0]["source_url"], "https://example.com/holdings")
        self.assertEqual(rows[0]["adjusted_price_sessions"], 250)

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
        theme_row = _theme_csv_row({
            "id": "theme", "name": "Theme", "level": "Theme",
            "theme_watchlist_breadth": {"21": {"value": 66.7, "above_count": 10, "valid_count": 15, "change_5_pp": 4.0}},
        })
        self.assertEqual(theme_row["theme_breadth21_above"], 10)
        self.assertEqual(theme_row["theme_breadth21_valid"], 15)
        self.assertEqual(theme_row["theme_breadth21_change_5_pp"], 4.0)
        self.assertIn("theme_breadth21_above", __import__("scripts.generate_dashboard", fromlist=["THEME_EXPORT_COLUMNS"]).THEME_EXPORT_COLUMNS)

        stock = {"ticker": "AAA", "returns": {"5": metric(0.1075), "21": metric(0.1075), "63": metric(0.2)}, "excess_returns": {"5": metric(0.0125), "21": metric(0.025), "63": metric(-0.01)}}
        exported = _all_selected({"themes": [{"name": "Theme", "id": "theme", "anchor": "ETF", "selected": [stock]}]}, 15)[0]
        self.assertAlmostEqual(exported["return5_pct"], 10.75)
        self.assertAlmostEqual(exported["excess5_pp"], 1.25)
        self.assertIn("return21_pct", EXPORT_COLUMNS)
        self.assertNotIn("return21", EXPORT_COLUMNS)

    def test_dashboard_payload_omits_large_audit_collections_but_keeps_ui_fields(self) -> None:
        payload = _dashboard_snapshot({
            "themes": [{"name": "Theme", "selected": [], "history": [1], "stock_audit": [2], "holdings_breadth": {"21": {"value": 50}}, "theme_watchlist_breadth": {"21": {"value": 50, "coverage_pct": 100, "prior": {"value": 40}}}}],
            "candidate_metrics": [1], "registry_diagnostics": [2], "source_matrix": [3],
            "settings": {"watchlist_capacity": 20},
        })
        self.assertNotIn("candidate_metrics", payload)
        self.assertNotIn("registry_diagnostics", payload)
        self.assertNotIn("source_matrix", payload)
        self.assertNotIn("stock_audit", payload["themes"][0])
        self.assertIn("selected", payload["themes"][0])
        self.assertNotIn("holdings_breadth", payload["themes"][0])
        self.assertEqual(payload["themes"][0]["theme_watchlist_breadth"]["21"]["value"], 50)
        self.assertNotIn("coverage_pct", payload["themes"][0]["theme_watchlist_breadth"]["21"])
        self.assertNotIn("prior", payload["themes"][0]["theme_watchlist_breadth"]["21"])

    def test_compact_snapshot_uses_only_canonical_theme_breadth_names(self) -> None:
        snapshot = {
            "themes": [{
                "id": "theme", "name": "Theme", "anchor": "ETF", "selected": [],
                "etf_breadth21_pct": 66.7, "breadth21_change_5_pp": 4.0,
                "theme_breadth21_pct": 66.7, "theme_breadth21_above": 10, "theme_breadth21_valid": 15,
                "theme_breadth21_change_5_pp": 4.0,
                "theme_watchlist_breadth": {"21": {"value": 66.7, "coverage_pct": 100, "above_count": 10, "valid_count": 15}},
            }],
            "context": [{"ticker": "SPY", "market_condition21": "Internal strength, index below EMA21", "field_status": {"input_version": "themescope-v6.2"}}],
            "comparisons": [{"id": "old-comparison"}],
        }
        primary = _primary_snapshot(snapshot)
        row = primary["themes"][0]
        self.assertEqual(row["theme_breadth21_pct"], 66.7)
        self.assertEqual(row["theme_breadth21_above"], 10)
        self.assertEqual(row["theme_breadth21_valid"], 15)
        self.assertNotIn("etf_breadth21_pct", row)
        self.assertNotIn("breadth21_change_5_pp", row)
        self.assertNotIn("market_condition21", primary["context"][0])
        self.assertNotIn("input_version", primary["context"][0].get("field_status", {}))
        self.assertNotIn("comparisons", primary)
        self.assertNotIn("coverage_pct", row["theme_watchlist_breadth"]["21"])

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

    def test_offline_rerender_rebuilds_compact_index_maps_and_fixed_universe_change(self) -> None:
        raw = {"v5": {"index_universes": {
            "SPY": {"rows": [{"ticker": "AAA", "company": "Alpha", "security_type": "EQUITY"}]},
            "QQQ": {"rows": [{"ticker": "BBB", "company": "Beta", "security_type": "EQUITY"}]},
            "IWM": {"rows": [{"ticker": "CCC", "company": "Gamma", "security_type": "Equity", "country": "United States"}]},
        }}}
        _rehydrate_index_universes(raw)
        mapped = raw["v5"]["mapped_universes"]
        self.assertEqual(mapped["SPY"]["companies"][0]["symbols"], ["AAA"])
        self.assertEqual(mapped["QQQ"]["companies"][0]["symbols"], ["BBB"])
        self.assertEqual(mapped["IWM"]["companies"][0]["symbols"], ["CCC"])

        old = [{"ticker": "QQQ", "index_breadth": {"21": {"value": 50.0, "status": "valid", "valid_count": 100}}, "breadth21_t_minus_5": None}]
        current = [{"ticker": "QQQ", "field_status": {"breadth21_t_minus_5": {"value": 45.0, "status": "valid"}}, "breadth21_t_minus_5": 45.0}]
        _retain_imported_index_metrics({"context": current, "session_date": "2026-10-23"}, old)
        self.assertEqual(current[0]["index_breadth"]["21"]["value"], 50.0)
        self.assertEqual(current[0]["breadth21_change_5_pp"], 5.0)


if __name__ == "__main__":
    unittest.main()
