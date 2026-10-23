"""v6.2 market presentation facts and instrument-specific volatility fields."""
import json
import unittest
from datetime import date, timedelta
from pathlib import Path

from src.themescope.presentation import enrich, _hkt_display


ROOT = Path(__file__).resolve().parents[1]


class PresentationV61Tests(unittest.TestCase):
    def test_utc_retrieval_timestamp_is_converted_to_explicit_hkt(self):
        self.assertEqual(_hkt_display('2026-10-23T18:53:49+00:00'), '24 Oct 2026, 02:53 AM HKT')

    def test_iwm_prices_and_vix_context_are_separate_from_breadth(self):
        end = date(2026, 10, 22)
        dates = [(end - timedelta(days=i)).isoformat() for i in range(279, -1, -1)]
        def chart(symbol, base):
            observations = [
                {"date": day, "close": base + index / 10, "adj_close": base + index / 10, "volume": 1000000}
                for index, day in enumerate(dates)
            ]
            return {"symbol": symbol, "url": "https://data.example/" + symbol, "retrieved_at": "2026-10-23T18:00:00+00:00", "meta": {"symbol": symbol, "currency": "USD", "instrumentType": "INDEX" if symbol == "^VIX" else "ETF"}, "events": {"splits": {}}, "observations": observations}

        raw = {"session_calendar": dates, "charts": {"SPY": chart("SPY", 500), "QQQ": chart("QQQ", 400), "IWM": chart("IWM", 200), "^VIX": chart("^VIX", 15)}}
        snapshot = {
            "session_date": dates[-1], "settings": json.loads((ROOT / "config/themes.json").read_text())["settings"],
            "context": [{"ticker": ticker, "returns": {}} for ticker in ("SPY", "QQQ", "IWM")],
            "themes": [], "volatility_context": [{"ticker": "^VIX", "instrument_type": "volatility_index", "source_status": "available"}],
        }
        result = enrich(snapshot, raw)
        iwm = next(row for row in result["context"] if row["ticker"] == "IWM")
        vix = result["volatility_context"][0]
        self.assertEqual(iwm["price_status"], "valid")
        self.assertGreater(iwm["price_close"], 0)
        self.assertEqual(iwm["price_session_date"], dates[-1])
        self.assertEqual(vix["instrument_type"], "volatility_index")
        self.assertEqual(vix["observation_date"], dates[-1])
        self.assertEqual(vix["trailing_1y_observations"], 252)
        self.assertIsNotNone(vix["trailing_1y_percentile"])
        self.assertFalse(any("breadth" in key for key in vix))
        self.assertEqual(vix["source_status"], "available")
        self.assertEqual(vix["vix_direction_1d"], "up")
        self.assertEqual(vix["vix_direction_5d"], "up")
        self.assertEqual(vix["vix_direction_21d"], "up")
        self.assertEqual(vix["vix_direction_summary"], "Volatility increased across all displayed periods.")
        self.assertEqual(len(vix["history"]), 63)
        self.assertIsNotNone(vix["trailing_1y_percentile"])

    def test_vix_direction_summary_handles_falling_and_mixed_changes(self):
        end = date(2026, 10, 22)
        dates = [(end - timedelta(days=i)).isoformat() for i in range(29, -1, -1)]
        def run(values):
            chart = {"meta": {"instrumentType": "INDEX"}, "observations": [
                {"date": day, "close": value, "adj_close": value, "volume": 1000}
                for day, value in zip(dates, values)
            ]}
            raw = {"session_calendar": dates, "charts": {"^VIX": chart}}
            snapshot = {"session_date": dates[-1], "settings": {}, "context": [], "themes": [], "volatility_context": [{"ticker": "^VIX"}]}
            return enrich(snapshot, raw)["volatility_context"][0]
        falling = run([40 - i for i in range(30)])
        self.assertEqual(falling["vix_direction_summary"], "Volatility decreased across all displayed periods.")
        mixed_values = [30.0] * 30
        mixed_values[-22] = 25.0
        mixed_values[-6] = 18.0
        mixed_values[-2] = 21.0
        mixed_values[-1] = 20.0
        mixed = run(mixed_values)
        self.assertEqual((mixed["vix_direction_1d"], mixed["vix_direction_5d"], mixed["vix_direction_21d"]), ("down", "up", "down"))
        self.assertEqual(mixed["vix_direction_summary"], "Volatility direction is mixed across the displayed periods.")

    def test_vix_percentile_uses_average_ties_in_a_full_trailing_window(self):
        end = date(2026, 10, 22)
        dates = [(end - timedelta(days=i)).isoformat() for i in range(251, -1, -1)]
        chart = {"meta": {"instrumentType": "INDEX"}, "observations": [
            {"date": day, "close": 20.0, "adj_close": 20.0, "volume": 1000}
            for day in dates
        ]}
        raw = {"session_calendar": dates, "charts": {"^VIX": chart}}
        snapshot = {"session_date": dates[-1], "settings": {}, "context": [], "themes": [], "volatility_context": [{"ticker": "^VIX"}]}
        vix = enrich(snapshot, raw)["volatility_context"][0]
        self.assertEqual(vix["trailing_1y_observations"], 252)
        self.assertEqual(vix["trailing_1y_percentile"], 50.0)


if __name__ == "__main__":
    unittest.main()
