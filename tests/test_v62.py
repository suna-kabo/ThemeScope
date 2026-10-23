"""v6.2 calculations and IWM source mapping regression checks."""
from datetime import date, timedelta
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.themescope.v5 import (
    breadth_change,
    collect_inputs,
    historical_rank_metrics,
    map_iwm_universe,
    metric,
    normalize_price_symbol,
)
from scripts.generate_dashboard import _ensure_v61_market_records, _load_iwm_sidecar, _write_iwm_sidecar


class V62IwmTests(unittest.TestCase):
    def test_iwm_direct_tickers_normalize_and_keep_sec_optional(self):
        source = {"rows": [
            {"ticker": "MOG A", "company": "MOOG INC CLASS A", "security_type": "Equity"},
            {"ticker": "MOG B", "company": "MOOG INC CLASS B", "security_type": "Equity"},
            {"ticker": "TOWN", "company": "TowneBank", "security_type": "Equity"},
            {"ticker": "CVI", "company": "CVR ENERGY INC", "security_type": "Equity"},
            {"ticker": "INH", "company": "INHIBRX INC CVR", "security_type": "Equity"},
            {"ticker": "", "company": "Cash balance", "security_type": "Cash"},
            {"ticker": "-", "company": "Issuer without a ticker", "security_type": "Equity"},
        ]}
        mapping = {"listings": {
            "MOG-A": {"ticker": "MOG-A", "cik": "0000000055"},
            "MOG-B": {"ticker": "MOG-B", "cik": "0000000055"},
        }}
        result = map_iwm_universe(source, mapping)
        by_id = {row["company_id"]: row for row in result["companies"]}
        moog = by_id["cik:0000000055"]
        self.assertEqual(moog["symbols"], ["MOG-A", "MOG-B"])
        self.assertTrue(any("TOWN" in row["symbols"] for row in result["companies"]))
        self.assertTrue(any("CVI" in row["symbols"] for row in result["companies"]))  # CVR Energy is a listed company, not a CVR security.
        self.assertEqual(result["classified_equity_rows"], 6)
        self.assertEqual(result["eligible_equity_rows"], 4)
        self.assertEqual(result["normalization_failure_count"], 1)
        self.assertEqual(result["issuer_description_exclusions"], 1)
        self.assertEqual(result["sec_verified_company_count"], 1)
        self.assertGreaterEqual(result["direct_ticker_company_count"], 2)
        self.assertEqual(normalize_price_symbol("MOG A"), "MOG-A")
        self.assertEqual(normalize_price_symbol("BRK.B"), "BRK-B")

    def test_collector_requests_iwm_symbols_without_sec_mapping(self):
        holdings = {"IWM": {"as_of": "2026-10-22", "rows": [
            {"ticker": "MOG A", "company": "MOOG INC CLASS A", "security_type": "Equity"},
            {"ticker": "TOWN", "company": "TowneBank", "security_type": "Equity"},
        ]}}
        charts_requested = []
        def fake_chart(symbol, years=2):
            charts_requested.append((symbol, years))
            dates = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(210)]
            return {"symbol": symbol, "meta": {"instrumentType": "EQUITY"}, "observations": [
                {"date": day, "close": 100.0, "adj_close": 100.0, "volume": 1000.0}
                for day in dates
            ]}
        with patch("src.themescope.v5.fetch_universes", return_value=({"SPY": {"rows": []}, "QQQ": {"rows": []}}, {"listings": {}})), \
             patch("src.themescope.v5.fetch_yahoo_chart", side_effect=fake_chart), \
             patch("src.themescope.v5.time.sleep"), \
             patch("src.themescope.v5._YAHOO_BLOCKED_HOSTS", set()):
            result = collect_inputs({}, {}, context_holdings={"IWM": holdings["IWM"]}, interval=0)
        self.assertEqual({symbol for symbol, _ in charts_requested}, {"MOG-A", "TOWN"})
        self.assertTrue(all(years == 1 for _, years in charts_requested))
        self.assertEqual(set(result["iwm_breadth_charts"]), {"MOG-A", "TOWN"})
        self.assertEqual(result["iwm_breadth_diagnostics"]["direct_ticker_companies"], 2)
        self.assertEqual(result["iwm_breadth_diagnostics"]["history_qualified"], 2)

    def test_iwm_sidecar_round_trips_normalized_chart_payloads(self):
        charts = {"ABC": {"symbol": "ABC", "url": "https://query1.example/ABC", "meta": {"instrumentType": "EQUITY"}, "observations": [{"date": "2026-10-22", "close": 10.0, "adj_close": 9.9, "volume": 100.0}]}}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "iwm_breadth_prices.csv.gz"
            _write_iwm_sidecar(path, charts)
            raw = {"v5": {}}
            _load_iwm_sidecar(raw, path.read_bytes())
        self.assertEqual(raw["v5"]["iwm_breadth_charts"], charts)

    def test_iwm_price_collection_diagnostics_survive_snapshot_remapping(self):
        snapshot = {"session_date": "2026-10-22", "context": [{"ticker": "IWM"}]}
        raw = {
            "context_holdings": {"IWM": {"as_of": "2026-10-22", "rows": []}},
            "v5": {"security_mapping": {"listings": {}}, "mapped_universes": {
                "IWM": {"price_collection": {"new_requests": 20, "downloaded_history_count": 18}}
            }},
        }
        _ensure_v61_market_records(snapshot, raw, {"context_symbols": ["IWM"], "volatility_symbols": []})
        self.assertEqual(raw["v5"]["mapped_universes"]["IWM"]["price_collection"], {
            "new_requests": 20, "downloaded_history_count": 18,
        })


class V62MetricTests(unittest.TestCase):
    def test_five_session_breadth_change_requires_both_valid_observations(self):
        result = breadth_change(metric(63.0), metric(42.0), "2026-10-22", "2026-10-15")
        self.assertEqual(result["value"], 21.0)
        self.assertEqual(result["current_session"], "2026-10-22")
        missing = breadth_change(metric(63.0), metric(reason="below 80% completeness"), "2026-10-22", "2026-10-15")
        self.assertIsNone(missing["value"])
        self.assertIn("five-session-prior breadth unavailable", missing["reason"])

    def test_historical_rank_recomputes_scores_and_averages_ties(self):
        calendar = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(100)]
        charts = {"SPY": {"observations": [{"date": day, "adj_close": 100.0} for day in calendar]}}
        themes = []
        for i in range(10):
            ticker = f"ETF{i}"
            charts[ticker] = {"observations": [{"date": day, "adj_close": 100.0} for day in calendar]}
            themes.append({"id": f"theme-{i}", "anchor": ticker})
        result = historical_rank_metrics(themes, charts, calendar, calendar[-1], {"theme_score_weights": {"current_strength": 0.6, "medium_strength": 0.4}}, 10)
        self.assertEqual({row["rank_t_minus_5"] for row in result.values()}, {5.5})
        self.assertEqual({row["historical_rank_peer_count"] for row in result.values()}, {10})
        self.assertTrue(all(row["historical_rank_status"] == "valid" for row in result.values()))
        too_few = historical_rank_metrics(themes[:9], charts, calendar, calendar[-1], {"theme_score_weights": {"current_strength": 0.6, "medium_strength": 0.4}}, 10)
        self.assertTrue(all(row["rank_t_minus_5"] is None for row in too_few.values()))
        self.assertTrue(all("Requires 10 valid historical ETF peers" in row["rank_t_minus_5_reason"] for row in too_few.values()))


if __name__ == "__main__":
    unittest.main()
