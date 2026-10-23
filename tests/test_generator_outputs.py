from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.generate_dashboard import RUN_OUTPUT_FILES, _write_run_bundle, make_source_matrix


class RunBundleTests(unittest.TestCase):
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
