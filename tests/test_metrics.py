from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from src.themescope.metrics import (
    breadth_label_from_fraction,
    completed_session,
    excess_metric,
    relative_state,
    relative_wealth_change,
    return_metric,
    select_candidates,
    split_adjusted_observations,
    trend_metric,
)


class MetricAcceptanceTests(unittest.TestCase):
    def test_equal_asset_and_benchmark_returns_have_zero_excess_and_relative_change(self) -> None:
        asset = {"value": 0.10, "status": "valid", "session_date": "2026-10-21"}
        benchmark = {"value": 0.10, "status": "valid", "session_date": "2026-10-21"}
        self.assertAlmostEqual(excess_metric(asset, benchmark)["value"], 0.0)
        self.assertAlmostEqual(relative_wealth_change(0.10, 0.10), 0.0)

    def test_excess_percentage_points_differ_from_relative_wealth_change(self) -> None:
        asset = {"value": 0.12, "status": "valid", "session_date": "2026-10-21"}
        benchmark = {"value": 0.08, "status": "valid", "session_date": "2026-10-21"}
        self.assertAlmostEqual(excess_metric(asset, benchmark)["value"], 0.04)
        self.assertAlmostEqual(relative_wealth_change(0.12, 0.08), 0.037037037, places=8)

    def test_relative_state_covers_all_signs_zero_and_missing(self) -> None:
        cases = {
            (1, 1): "Outperforming",
            (-1, -1): "Underperforming",
            (1, -1): "Short-term outperformance / medium-term underperformance",
            (-1, 1): "Short-term underperformance / medium-term outperformance",
            (0, 1): "Mixed",
            (1, 0): "Mixed",
            (0, 0): "Mixed",
            (None, 1): "Unavailable",
            (1, None): "Unavailable",
        }
        for inputs, expected in cases.items():
            with self.subTest(inputs=inputs):
                self.assertEqual(relative_state(*inputs), expected)

    def test_exact_endpoint_return_survives_an_interior_gap(self) -> None:
        calendar = [f"2026-10-{day:02d}" for day in range(1, 7)]
        chart = {"observations": [
            {"date": d, "adj_close": (100.0 if i == 0 else (None if i == 2 else 110.0))}
            for i, d in enumerate(calendar)
        ]}
        metric = return_metric(chart, calendar, calendar[-1], 5)
        self.assertEqual(metric["status"], "valid")
        self.assertAlmostEqual(metric["value"], 0.10)
        self.assertIn("interior session gap", metric["reason"])

    def test_missing_return_endpoint_is_unavailable(self) -> None:
        calendar = [f"2026-10-{day:02d}" for day in range(1, 7)]
        chart = {"observations": [{"date": d, "adj_close": (None if i == 0 else 100.0)} for i, d in enumerate(calendar)]}
        metric = return_metric(chart, calendar, calendar[-1], 5)
        self.assertEqual(metric["status"], "unavailable")
        self.assertIn("Missing adjusted-close endpoint", metric["reason"])

    def test_split_reconstruction_preserves_contemporaneous_dollar_turnover(self) -> None:
        ny = ZoneInfo("America/New_York")
        split_time = datetime(2020, 2, 3, 0, 0, tzinfo=ny).timestamp()
        chart = {
            "events": {"splits": {"2020-02-03": {"date": split_time, "numerator": 4, "denominator": 1}}},
            "observations": [
                {"date": "2020-01-31", "close": 25.0, "volume": 400.0},
                {"date": "2020-02-03", "close": 25.0, "volume": 400.0},
            ],
        }
        rows = split_adjusted_observations(chart)
        self.assertEqual(rows[0]["raw_close"], 100.0)
        self.assertEqual(rows[0]["raw_volume"], 100.0)
        self.assertEqual(rows[0]["dollar_volume_proxy"], 10000.0)
        self.assertEqual(rows[1]["dollar_volume_proxy"], 10000.0)

    def test_correctly_adjusted_split_does_not_create_price_return(self) -> None:
        calendar = ["2020-01-31", "2020-02-03"]
        chart = {"observations": [
            {"date": "2020-01-31", "adj_close": 25.0},
            {"date": "2020-02-03", "adj_close": 25.0},
        ]}
        metric = return_metric(chart, calendar, calendar[-1], 1)
        self.assertEqual(metric["status"], "valid")
        self.assertAlmostEqual(metric["value"], 0.0)

    def test_missing_close_only_invalidates_trend_not_adjusted_endpoint_return(self) -> None:
        from datetime import timedelta

        calendar = [(datetime(2026, 1, 1) + timedelta(days=i)).date().isoformat() for i in range(205)]
        observations = []
        for index, day in enumerate(calendar):
            observations.append({"date": day, "adj_close": 100.0 + index, "close": None if index == 10 else 100.0 + index})
        chart = {"observations": observations}
        ret = return_metric(chart, calendar, calendar[-1], 21)
        trend = trend_metric(chart, calendar, calendar[-1], {
            "ema21_warmup_sessions": 84,
            "ema21_slope_warmup_sessions": 89,
            "ema50_warmup_sessions": 200,
        })
        self.assertEqual(ret["status"], "valid")
        self.assertEqual(trend["status"], "unavailable")
        self.assertIn("EMA50", trend["reason"])

    def test_breadth_requires_valid_denominator_coverage_and_fresh_complete_review(self) -> None:
        self.assertEqual(breadth_label_from_fraction(8, 8, 10, True, True), ("Majority above EMA21", None))
        label, reason = breadth_label_from_fraction(8, 8, 11, True, True)
        self.assertEqual(label, "Unavailable")
        self.assertIn("80%", reason)
        self.assertEqual(breadth_label_from_fraction(0, 0, 0, True, True)[0], "Unavailable")
        self.assertIn("incomplete", breadth_label_from_fraction(8, 8, 10, True, False)[1])
        self.assertIn("stale", breadth_label_from_fraction(8, 8, 10, False, True)[1])

    def test_session_uses_prior_close_before_cutoff_and_verified_same_day_after(self) -> None:
        ny = ZoneInfo("America/New_York")
        chart = {"observations": [{"date": "2026-10-21"}, {"date": "2026-10-22"}], "meta": {"regularMarketTime": datetime(2026, 10, 22, 16, 2, tzinfo=ny).timestamp()}}
        self.assertEqual(completed_session(chart, datetime(2026, 10, 22, 16, 29, tzinfo=ny)), "2026-10-21")
        chart["meta"]["regularMarketTime"] = datetime(2026, 10, 22, 16, 1, tzinfo=ny).timestamp()
        self.assertEqual(completed_session(chart, datetime(2026, 10, 22, 16, 31, tzinfo=ny)), "2026-10-22")
        chart["meta"]["regularMarketTime"] = datetime(2026, 10, 21, 16, 1, tzinfo=ny).timestamp()
        self.assertEqual(completed_session(chart, datetime(2026, 10, 22, 16, 31, tzinfo=ny)), "2026-10-21")

    def test_selection_is_unique_and_15_is_nested_in_20(self) -> None:
        rows = [
            {"ticker": f"T{i:02d}", "company_id": f"C{i:02d}", "adv30_usd": 100 - i, "etf_weight_pct": i / 10, "market_cap_usd": 1000 - i, "excess21": 1 if i < 5 else (-1 if i < 10 else None)}
            for i in range(25)
        ]
        rows.append({**rows[0], "ticker": "T00B"})
        selected = select_candidates(rows, 20)
        self.assertEqual(len(selected), 20)
        self.assertEqual(len({row["ticker"] for row in selected}), 20)
        compact = selected[:15]
        expanded = selected[:20]
        self.assertEqual([r["ticker"] for r in compact], [r["ticker"] for r in expanded[:15]])
        self.assertTrue(all(row.get("selection_reason") for row in selected))


if __name__ == "__main__":
    unittest.main()
