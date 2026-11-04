"""v6 registry, eligibility, and snapshot-contract tests."""
import json
import unittest
from datetime import date, timedelta
from pathlib import Path

from src.themescope.cache import manifest_for_inputs
from src.themescope.v6 import _candidate_status, apply_v6, prepare_registry_themes, _validate_stock_watchlist_metadata


ROOT = Path(__file__).resolve().parents[1]


def chart_fixture(symbol, dates, close=100.0, volume=500_000.0):
    return {
        "symbol": symbol,
        "url": f"https://prices.example/{symbol}",
        "retrieved_at": "2026-10-23T16:00:00+00:00",
        "meta": {"symbol": symbol, "currency": "USD", "instrumentType": "ETF"},
        "events": {"splits": {}},
        "observations": [
            {"date": day, "close": close + index / 10, "adj_close": close + index / 10, "volume": volume}
            for index, day in enumerate(dates)
        ],
    }


class V6RegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads((ROOT / "config/themes.json").read_text(encoding="utf-8"))

    def test_seed_registry_is_complete_and_candidates_are_unique_within_exposure(self):
        rows = self.registry["themes"]
        sectors = [row for row in rows if row.get("level") == "Sector"]
        self.assertEqual(len(rows), 65)
        self.assertEqual(len(sectors), 11)
        self.assertEqual(len({row["id"] for row in rows}), 65)
        self.assertTrue(all(row.get("candidate_anchors") for row in rows))
        self.assertTrue(all(len(row["candidate_anchors"]) == len(set(row["candidate_anchors"])) for row in rows))
        for row in rows:
            self.assertEqual(set(row.get("candidate_reviews", {})), set(row["candidate_anchors"]))
            for ticker, review in row["candidate_reviews"].items():
                if review.get("status") in {"reviewed", "rejected"}:
                    self.assertTrue(review.get("reviewed_date"), (row["id"], ticker))
                    self.assertTrue(str(review.get("source_url", "")).startswith("https://"), (row["id"], ticker))
                    self.assertTrue(review.get("rationale"), (row["id"], ticker))
            self.assertTrue(all(review.get("status") in {"reviewed", "rejected"} for review in row["candidate_reviews"].values()))
        self.assertEqual(
            {row["id"] for row in sectors},
            {"sector-communication-services", "sector-consumer-discretionary", "sector-consumer-staples", "sector-energy", "sector-financials", "sector-health-care", "sector-industrials", "sector-information-technology", "sector-materials", "sector-real-estate", "sector-utilities"},
        )
        self.assertTrue(all(row["id"].startswith("theme-") for row in rows if row.get("level") != "Sector"))
        self.assertEqual(sum(bool(row.get("holdings_source")) for row in rows), 17)

    def test_candidate_requires_price_mandate_liquidity_but_not_holdings_breadth(self):
        dates = [(date(2026, 10, 22) - timedelta(days=i)).isoformat() for i in range(69, -1, -1)]
        session = dates[-1]
        record = {
            "id": "test-theme", "name": "Test Theme", "anchor": "TST", "candidate_anchors": ["TST"],
            "unleveraged_equity_etf_review": True, "mandate_review_date": "2026-10-22",
            "anchor_url": "https://issuer.example/TST", "anchor_instrument_review": "Long-only unleveraged equity exposure.",
            "holdings_source": {"provider": "Issuer", "method": "csv", "url": "https://issuer.example/holdings.csv"},
        }
        raw = {
            "charts": {"TST": chart_fixture("TST", dates)},
            "session_calendar": dates,
            "holdings": {"TST": {"as_of": session, "retrieved_at": "2026-10-23T16:00:00+00:00", "rows": [{"ticker": "AAA"}]}},
            "v5": {"mapped_universes": {}},
        }
        snapshot = {"session_date": session, "run_date": session}
        result = _candidate_status(record, "TST", raw, snapshot, self.registry["settings"])
        self.assertEqual(result["status"], "eligible")
        self.assertGreaterEqual(result["valid_history_sessions"], 64)
        self.assertGreaterEqual(result["adv30_usd"], self.registry["settings"]["anchor_adv30_floor_usd"])
        self.assertIsNone(result["aum_usd"])
        self.assertIsNone(result["median_spread_pct"])
        no_holdings_parser = {key: value for key, value in record.items() if key != "holdings_source"}
        result_without_parser = _candidate_status(no_holdings_parser, "TST", {**raw, "holdings": {}}, snapshot, self.registry["settings"])
        self.assertEqual(result_without_parser["status"], "eligible")
        self.assertEqual(result_without_parser["breadth_status"], "breadth_not_configured")
        self.assertTrue(any(reason == "Official holdings source is not configured for this ETF." for reason in result_without_parser["breadth_reasons"]))

    def test_missing_holdings_parser_does_not_reject_a_reviewed_anchor(self):
        dates = [(date(2026, 10, 22) - timedelta(days=i)).isoformat() for i in range(69, -1, -1)]
        record = {"id": "test-theme", "name": "Test Theme", "anchor": "ALT", "candidate_anchors": ["ALT"], "unleveraged_equity_etf_review": True, "mandate_review_date": "2026-10-22", "anchor_url": "https://issuer.example/ALT", "anchor_instrument_review": "Long-only unleveraged equity exposure."}
        raw = {"charts": {"ALT": chart_fixture("ALT", dates)}, "session_calendar": dates, "holdings": {}}
        result = _candidate_status(record, "ALT", raw, {"session_date": dates[-1]}, self.registry["settings"])
        self.assertEqual(result["status"], "eligible")
        self.assertFalse(any("holdings" in reason.lower() for reason in result["reasons"]))
        self.assertEqual(result["breadth_status"], "breadth_not_configured")
        self.assertTrue(any(reason == "Official holdings source is not configured for this ETF." for reason in result["breadth_reasons"]))

    def test_alternate_candidate_requires_its_own_mandate_review(self):
        dates = [(date(2026, 10, 22) - timedelta(days=i)).isoformat() for i in range(69, -1, -1)]
        record = {
            "id": "test-theme", "name": "Test Theme", "anchor": "TST", "candidate_anchors": ["TST", "ALT"],
            "candidate_reviews": {"TST": {"status": "reviewed", "reviewed_date": "2026-10-22", "source_url": "https://issuer.example/TST", "rationale": "Long-only equity mandate."}},
        }
        raw = {"charts": {"ALT": chart_fixture("ALT", dates)}, "session_calendar": dates}
        result = _candidate_status(record, "ALT", raw, {"session_date": dates[-1]}, self.registry["settings"])
        self.assertEqual(result["mandate_review_status"], "incomplete")
        self.assertTrue(any(reason.startswith("ETF mandate review is incomplete") for reason in result["reasons"]))

    def test_rejected_candidate_has_complete_review_but_is_not_eligible(self):
        dates = [(date(2026, 10, 22) - timedelta(days=i)).isoformat() for i in range(69, -1, -1)]
        rationale = "The current prospectus permits total-return swaps for the fund's core exposure."
        record = {
            "id": "theme-test", "name": "Test", "anchor": "BAD", "candidate_anchors": ["BAD"],
            "candidate_reviews": {"BAD": {
                "status": "rejected", "reviewed_date": "2026-10-24",
                "source_url": "https://issuer.example/BAD/prospectus", "rationale": rationale,
            }},
        }
        raw = {"charts": {"BAD": chart_fixture("BAD", dates)}, "session_calendar": dates}
        result = _candidate_status(record, "BAD", raw, {"session_date": dates[-1]}, self.registry["settings"])
        self.assertEqual(result["status"], "ineligible")
        self.assertEqual(result["mandate_review_status"], "rejected")
        self.assertTrue(result["mandate_review_complete"])
        self.assertIn("ETF mandate review rejected: " + rationale, result["reasons"])
        self.assertFalse(any(reason.startswith("ETF mandate review is incomplete") for reason in result["reasons"]))

    def test_selected_alternate_gets_its_own_price_metrics_before_scoring(self):
        dates = [(date(2026, 10, 22) - timedelta(days=i)).isoformat() for i in range(69, -1, -1)]
        record = {
            "id": "theme-test", "name": "Test Theme", "level": "Theme", "anchor": "OLD",
            "candidate_anchors": ["OLD", "NEW"], "preferred_candidate": "NEW",
            "candidate_reviews": {"NEW": {
                "status": "reviewed", "reviewed_date": "2026-10-24",
                "source_url": "https://issuer.example/NEW/prospectus", "rationale": "Long-only equity-index objective.",
            }},
        }
        raw = {
            "charts": {"NEW": chart_fixture("NEW", dates), "SPY": chart_fixture("SPY", dates)},
            "session_calendar": dates,
        }
        snapshot = {
            "session_date": dates[-1], "settings": self.registry["settings"],
            "themes": [{"id": "theme-test", "name": "Test Theme", "anchor": "OLD", "selected": [{"ticker": "STALE"}]}],
        }
        prepare_registry_themes(snapshot, raw, {"themes": [record]})
        self.assertEqual(len(snapshot["themes"]), 1)
        theme = snapshot["themes"][0]
        self.assertEqual(theme["anchor"], "NEW")
        self.assertEqual(theme["selected"], [])
        self.assertEqual(theme["returns"]["21"]["status"], "valid")
        self.assertEqual(theme["excess_returns"]["63"]["status"], "valid")
        self.assertTrue(theme["anchor_screen"]["anchor_screen_valid"])
        self.assertEqual(theme["anchor_screen"]["mandate_review_note"], "Long-only equity-index objective.")

    def test_v6_snapshot_records_unavailable_sources_and_candidate_reasons(self):
        session = "2026-10-22"
        record = {"id": "theme-test", "name": "Test", "anchor": "TST", "candidate_anchors": ["TST"], "level": "Theme", "charter": "Review required", "charter_status": "needs_review", "unleveraged_equity_etf_review": True, "mandate_review_date": "2026-10-22", "anchor_url": "https://issuer.example/TST", "anchor_instrument_review": "Long-only unleveraged equity exposure.", "holdings_source": {"provider": "Issuer", "method": "csv", "url": "https://issuer.example/holdings.csv"}}
        theme = {"id": "theme-test", "name": "Test", "anchor": "TST", "selected": [], "returns": {}, "excess_returns": {}, "field_status": {}}
        snapshot = {"session_date": session, "run_date": session, "generated_at": "2026-10-23T16:00:00+00:00", "themes": [theme], "context": [], "settings": self.registry["settings"]}
        raw = {"charts": {}, "holdings": {}, "quotes": {}, "errors": {"charts": {}, "holdings": {}, "quotes": {}}, "v5": {}}
        result = apply_v6(snapshot, raw, {"registry_version": "6.1", "methodology_version": "6.1", "themes": [record]})
        self.assertEqual(result["schema_version"], "6.2")
        self.assertEqual(result["theme_registry_version"], "6.1")
        self.assertEqual(result["resolved_market_session"], session)
        self.assertEqual(result["themes"], [])
        self.assertEqual(result["registry_diagnostics"][0]["status"], "inactive_this_run")
        self.assertEqual(result["source_status"]["aum"]["status"], "unavailable")
        self.assertEqual(result["source_status"]["breadth_histories"]["status"], "unavailable")
        self.assertTrue(result["registry_diagnostics"][0]["candidates"][0]["reasons"])

    def test_sector_watchlist_intersects_official_holding_with_sourced_sector_classification(self):
        dates = [(date(2026, 10, 22) - timedelta(days=i)).isoformat() for i in range(69, -1, -1)]
        session = dates[-1]

        def stock_chart(symbol):
            chart = chart_fixture(symbol, dates, close=50, volume=1_000_000)
            chart["meta"].update({"instrumentType": "EQUITY", "fullExchangeName": "Nasdaq Global Select Market"})
            return chart

        record = {
            "id": "sector-communication-services", "name": "Communication Services", "level": "Sector",
            "anchor": "XLC", "candidate_anchors": ["XLC"], "preferred_candidate": "XLC",
            "unleveraged_equity_etf_review": True, "mandate_review_date": "2026-10-22",
            "anchor_url": "https://issuer.example/XLC", "anchor_instrument_review": "Long-only unleveraged equity exposure.",
            "holdings_source": {"provider": "Issuer", "method": "csv", "url": "https://issuer.example/XLC.csv"},
        }
        company = {"company_id": "1", "company": "Alpha Inc", "symbols": ["AAA"], "source_tickers": ["AAA"], "sector": "Communication Services"}
        snapshot = {
            "session_date": session, "run_date": session, "generated_at": "2026-10-23T16:00:00+00:00",
            "context": [{"ticker": "SPY", "returns": {"21": {"value": 0.01}, "63": {"value": 0.02}}}],
            "themes": [{"id": record["id"], "name": record["name"], "level": "Sector", "anchor": "XLC", "selected": [], "returns": {}, "excess_returns": {}, "field_status": {}}],
            "settings": self.registry["settings"],
        }
        raw = {
            "charts": {"XLC": chart_fixture("XLC", dates)},
            "session_calendar": dates,
            "holdings": {"XLC": {"as_of": session, "url": "https://issuer.example/XLC.csv", "rows": [{"ticker": "AAA", "company": "Alpha Inc", "weight_pct": 4.5}]}},
            "quotes": {"AAA": {"exchange": "NASDAQ-GS", "market_cap_usd": 3_000_000_000, "sector": "Communication Services", "industry": "Wireless", "url": "https://nasdaq.example/AAA", "retrieved_at": "2026-10-23T16:00:00+00:00"}},
            "errors": {"charts": {}, "quotes": {}, "holdings": {}},
            "v5": {
                "charts": {"AAA": stock_chart("AAA")},
                "index_universes": {"SPY": {"url": "https://index.example/sp500", "as_of": session}},
                "mapped_universes": {"SPY": {"companies": [company]}, "XLC": {"companies": [company]}},
            },
        }
        result = apply_v6(snapshot, raw, {"registry_version": "6.0", "themes": [record]})
        sector = result["themes"][0]
        self.assertEqual(len(sector["selected"]), 1)
        self.assertEqual(sector["selected"][0]["ticker"], "AAA")
        self.assertEqual(sector["selected"][0]["membership_tag"], "Core")
        self.assertIn("current S&P 500 source classifies", sector["selected"][0]["membership_rationale"])
        self.assertEqual(sector["stock_scope"], "Curated watchlist")
        self.assertTrue(sector["has_curated_watchlist"])
        self.assertEqual(sector["curated_watchlist_count"], 1)

    def test_stock_watchlist_validator_rejects_contradictory_metadata(self):
        snapshot = {"themes": [{"id": "theme-test", "selected": [{}], "stock_scope": "ETF-only", "has_curated_watchlist": False, "curated_watchlist_count": 0, "stock_drilldown_status": "not_configured"}]}
        with self.assertRaisesRegex(ValueError, "curated_watchlist_count does not match"):
            _validate_stock_watchlist_metadata(snapshot)

    def test_manifest_hashes_normalized_inputs_deterministically(self):
        raw = {"charts": {"AAA": {"url": "https://example/AAA", "observations": [{"date": "2026-10-22", "close": 5}]}}, "holdings": {}, "quotes": {}}
        first = manifest_for_inputs(raw, "2026-10-23T00:00:00+00:00")
        second = manifest_for_inputs(raw, "2026-10-23T00:00:00+00:00")
        self.assertEqual(first, second)
        self.assertEqual(len(first[0]["sha256"]), 64)
        self.assertEqual(first[0]["payload_kind"], "normalized_source_payload")


if __name__ == "__main__":
    unittest.main()
