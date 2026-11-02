import tempfile
import unittest
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.themescope.approved_rules import ACTION_SENTENCES, STATES, canonical_decision, market_direction, price_state, priority
from src.themescope.manual_csv import CSVValidationError, breadth, parse_csv, percentile, theme_score, theme_state, _row_fields
from scripts.generate_dashboard import _run_manual_csv


HEADER = (
    'Symbol,Description,Price,"Price change %, 1 day",Market capitalization,'
    '"Performance %, 1 week","Performance %, 1 month","Performance %, 3 months",'
    'Industry,Sector,Exchange,"Exponential moving average, 21, 1 day",'
    '"Exponential moving average, 50, 1 day","Average true range %, 14, 1 day",'
    '"Price × volume (turnover), 1 day","Price × average volume, 30 days",'
    '"Relative volume, 1 day",Upcoming earnings date,Unused column\n'
)
ROW = 'AAA,Alpha,20,1,3000000000,2,3,4,Software,Technology,NASDAQ,19,18,2,30000000,25000000,1.2,,ignored\n'


class ManualCSVTests(unittest.TestCase):
    def _csv(self, text):
        temporary = tempfile.TemporaryDirectory()
        path = Path(temporary.name) / "fixture.csv"
        path.write_text(text, encoding="utf-8")
        self.addCleanup(temporary.cleanup)
        return path

    def test_header_aliases_extra_columns_and_optional_earnings(self):
        rows, audit = parse_csv(self._csv(HEADER + ROW), "stock")
        self.assertEqual(rows[0]["ema21"], 19)
        self.assertIsNone(rows[0]["earnings_date"])
        self.assertIn("Unused column", audit["columns"])

    def test_etf_daily_change_fraction_and_unavailable(self):
        for raw,expected in [('1.234567',.01234567),('-2.5',-.025),('0',0)]:
            rows,_=parse_csv(self._csv(HEADER+ROW.replace('20,1,','20,'+raw+',')), 'etf')
            self.assertEqual(_row_fields(rows[0])['daily_change'],expected)
        self.assertIsNone(_row_fields({})['daily_change'])

    def test_unused_etf_blank_metrics_do_not_block_required_universe(self):
        unused = ROW.replace('AAA,Alpha', 'UNUSED,Unused').replace('20,1,3000000000,2,3,4,', '20,1,3000000000,,3,4,')
        path = self._csv(HEADER + ROW + unused)
        rows, audit = parse_csv(path, 'etf', required_symbols={'AAA'})
        self.assertEqual(len(rows), 2)
        self.assertIsNone(rows[1]['performance_1w_pct'])
        self.assertEqual(audit['numeric_warnings'][0]['symbol'], 'UNUSED')
        with self.assertRaisesRegex(CSVValidationError, 'required numeric value is blank'):
            parse_csv(path, 'etf', required_symbols={'AAA', 'UNUSED'})
        with self.assertRaisesRegex(CSVValidationError, 'required numeric value is blank'):
            parse_csv(path, 'stock', required_symbols={'AAA'})
        with self.assertRaisesRegex(CSVValidationError, 'invalid numeric value'):
            parse_csv(self._csv(HEADER + unused.replace(',,3,4,', ',bad,3,4,')), 'etf', required_symbols={'AAA'})

    def test_missing_invalid_market_cap_retains_stock(self):
        for value in ("", "NaN", "-1"):
            with self.subTest(value=value):
                rows, audit = parse_csv(self._csv(HEADER + ROW.replace("3000000000", value)), "stock")
                self.assertEqual(rows[0]["symbol"], "AAA")
                self.assertIsNone(rows[0]["market_cap"])
                if value: self.assertTrue(audit["numeric_warnings"])

    def test_duplicate_display_column_uses_first_and_records_ignored(self):
        header = HEADER.rstrip().replace("Unused column", '"Price change %, 1 day"') + "\n"
        rows, audit = parse_csv(self._csv(header + ROW.replace("ignored", "99")), "stock")
        self.assertEqual(rows[0]["change_1d_pct"], 1)
        self.assertEqual(audit["ignored_duplicate_columns"][0]["canonical"], "change_1d_pct")

    def test_duplicate_symbol_rejected(self):
        with self.assertRaisesRegex(CSVValidationError, "duplicate symbol AAA"):
            parse_csv(self._csv(HEADER + ROW + ROW), "stock")

    def test_percentiles_ties_equal_fallback_and_no_early_rounding(self):
        result = percentile({"a": 1.0, "b": 2.0, "c": 2.0, "d": 4.0}, 2)
        self.assertAlmostEqual(result["b"], 50.0)
        self.assertEqual(percentile({"a": 7, "b": 7}, 2), {"a": 50.0, "b": 50.0})
        precise = percentile({"a": 1.00001, "b": 1.00002, "c": 1.00003}, 2)
        self.assertEqual(precise, {"a": 0.0, "b": 50.0, "c": 100.0})

    def test_price_state_boundaries_and_missing(self):
        self.assertEqual(price_state(11, 10, 9), "Bullish")
        self.assertEqual(price_state(8, 9, 10), "Bearish")
        self.assertEqual(price_state(10, 10, 9), "Mixed")
        self.assertIsNone(price_state(None, 10, 9))

    def test_score_weights_four_states_and_exact_fifty(self):
        self.assertEqual(theme_score(75, 25), 55)
        self.assertEqual(theme_state(50, 50), "Leading")
        self.assertEqual(theme_state(50, 49.999), "Improving")
        self.assertEqual(theme_state(49.999, 50), "Fading")
        self.assertEqual(theme_state(49.999, 49.999), "Lagging")
        self.assertIsNone(theme_state(None, 50))
        # Score accepts only the two percentiles: 1W, EMA and Breadth are not arguments.
        self.assertEqual(theme_score(20, 80), theme_score(20, 80))

    def test_breadth_shared_set_and_exact_coverage_boundary(self):
        rows = [
            {"symbol": str(i), "price": 11, "ema21": 10, "ema50": 12}
            for i in range(8)
        ] + [{"symbol": "x", "price": None, "ema21": None, "ema50": None} for _ in range(2)]
        metric = breadth(rows, coverage_floor=.8)
        self.assertEqual(metric["21"]["valid_count"], 8)
        self.assertEqual(metric["50"]["valid_count"], 8)
        self.assertEqual(metric["21"]["value"], 100)
        self.assertEqual(metric["50"]["value"], 0)
        self.assertEqual(metric["state"], "Mixed")
        self.assertIsNone(breadth(rows + [{"symbol": "y"}], coverage_floor=.8)["21"]["value"])

    def test_complete_market_table_and_iwm_non_voting(self):
        breadth_cases = {"Positive": "Selective long", "Mixed": "Neutral", "Negative": "Selective short", None: "Unclassified"}
        for spy in ("Bullish", "Mixed", "Bearish"):
            for qqq in ("Bullish", "Mixed", "Bearish"):
                for combined, selective in breadth_cases.items():
                    expected = "Long bias" if spy == qqq == "Bullish" else "Short bias" if spy == qqq == "Bearish" else selective
                    self.assertEqual(market_direction(spy, qqq, combined), expected)
                    self.assertEqual(market_direction(spy, qqq, combined), market_direction(spy, qqq, combined))
        self.assertEqual(market_direction(None, "Bullish", "Positive"), "Unclassified")

    def test_every_priority_cell_and_ema50_guard_without_state_mutation(self):
        directions = ("Long bias", "Selective long", "Neutral", "Selective short", "Short bias", "Unclassified")
        for direction in directions:
            for state in STATES:
                close, ema = (11, 10) if direction in ("Long bias", "Selective long") else (9, 10)
                result = priority(direction, state, close, ema)
                self.assertIn("label", result)
                self.assertEqual(state, state)
        guarded = priority("Short bias", "Lagging", 11, 10)
        self.assertEqual(guarded["label"], "Observation only")
        self.assertEqual(priority("Short bias", "Lagging", 9, 10)["label"], "Primary short research")

    def test_canonical_decision_actions_groups_and_non_voting_context(self):
        self.assertEqual(set(ACTION_SENTENCES), {"Long bias", "Selective long", "Neutral", "Selective short", "Short bias", "Unclassified"})
        contexts = [
            {"ticker": "SPY", "price_state": "Bearish", "breadth_state": "Positive"},
            {"ticker": "QQQ", "price_state": "Bearish", "breadth_state": "Negative"},
            {"ticker": "IWM", "price_state": "Bullish", "breadth_state": "Mixed"},
        ]
        themes = []
        for index, (state, close) in enumerate((("Lagging", 9), ("Fading", 9), ("Leading", 9), ("Lagging", 11))):
            item = {"id": str(index), "theme_state": state, "price_close": close, "ema50": 10, "theme_score": index * 10}
            item["research_priority"] = priority("Short bias", state, close, 10)
            themes.append(item)
        decision = canonical_decision("2026-10-30", "2026-10-31T08:00:00+08:00", contexts, themes, "Short bias", "Mixed")
        self.assertEqual(decision["matrix_rule_id"], "unanimous-bearish")
        self.assertEqual(decision["market_classification"], "Short bias")
        self.assertEqual(decision["priority_groups"]["primary"], ["0"])
        self.assertEqual(decision["priority_groups"]["secondary"], ["1"])
        self.assertEqual(decision["priority_groups"]["exception"], ["2"])
        self.assertEqual(decision["priority_groups"]["observation"], ["3"])
        self.assertIn("context only", "context only")
        self.assertEqual(decision["iwm_price_state"], "Bullish")
        self.assertIn("does not reverse", decision["reason"])

    def test_theme_breadth_minimum_eight_and_eighty_percent(self):
        seven = [{"symbol": str(i), "price": 2, "ema21": 1, "ema50": 1} for i in range(7)]
        self.assertEqual(breadth(seven, minimum=8)["21"]["status"], "unavailable")
        eight = seven + [{"symbol": "8", "price": 2, "ema21": 1, "ema50": 1}, {"symbol": "missing"}, {"symbol": "missing2"}]
        self.assertEqual(breadth(eight, minimum=8)["21"]["status"], "valid")

    def test_failed_manual_import_preserves_previous_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "run"
            output.mkdir()
            (output / "dashboard.html").write_text("last success", encoding="utf-8")
            (output / "latest_snapshot.json").write_text(json.dumps({"session_date": "2026-10-30"}), encoding="utf-8")
            args = SimpleNamespace(as_of="2026-10-31", stock_csv=Path("s"), etf_csv=Path("e"), spy_csv=Path("p"), qqq_csv=Path("q"), iwm_csv=Path("i"))
            with patch("src.themescope.manual_csv.build_release", side_effect=CSVValidationError("invalid fixture")):
                self.assertEqual(_run_manual_csv(args, output, 0.0), 1)
            self.assertEqual((output / "dashboard.html").read_text(encoding="utf-8"), "last success")
            self.assertEqual(json.loads((output / "latest_snapshot.json").read_text())["session_date"], "2026-10-30")
            failed = json.loads((output / "failed_attempt_audit.json").read_text())
            self.assertTrue(failed["dashboard_preserved"])


if __name__ == "__main__":
    unittest.main()
