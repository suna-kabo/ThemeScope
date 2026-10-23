"""Calculations for the stateless, end-of-day watchlist snapshot."""

from __future__ import annotations

from datetime import date, datetime, time
from math import prod
from typing import Any, Iterable
from zoneinfo import ZoneInfo


NY = ZoneInfo("America/New_York")


def session_dates(chart: dict[str, Any]) -> list[str]:
    return [str(row["date"]) for row in chart.get("observations", [])]


def observation_map(chart: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["date"]): row for row in chart.get("observations", [])}


def completed_session(spy_chart: dict[str, Any], now: datetime) -> str | None:
    """Pick the latest prior session, or today's bar after a conservative cutoff."""
    dates = session_dates(spy_chart)
    if not dates:
        return None
    local_now = now.astimezone(NY)
    cutoff = datetime.combine(local_now.date(), time(16, 30), tzinfo=NY)
    today = local_now.date().isoformat()
    same_day_final = False
    if local_now >= cutoff and today in dates:
        marker = spy_chart.get("meta", {}).get("regularMarketTime")
        try:
            marker_time = datetime.fromtimestamp(float(marker), NY)
            same_day_final = marker_time.date().isoformat() == today
        except (TypeError, ValueError, OSError):
            same_day_final = False
    if same_day_final:
        eligible = [d for d in dates if d <= today]
    else:
        eligible = [d for d in dates if d < today]
    return max(eligible) if eligible else None


def _metric(value: float | None, status: str, reason: str, count: int | None, session: str | None) -> dict[str, Any]:
    return {
        "value": value,
        "status": status,
        "reason": reason,
        "observation_count": count,
        "session_date": session,
        "input_version": "yahoo-chart-adjusted-close-v1",
    }


def return_metric(
    chart: dict[str, Any], market_calendar: list[str], run_session: str, n: int
) -> dict[str, Any]:
    if run_session not in market_calendar:
        return _metric(None, "unavailable", "Run session is not in the benchmark session calendar", None, run_session)
    end_index = market_calendar.index(run_session)
    start_index = end_index - n
    if start_index < 0:
        return _metric(None, "unavailable", f"Fewer than {n + 1} benchmark sessions are available", None, run_session)
    start_date = market_calendar[start_index]
    price = observation_map(chart)
    first = price.get(start_date, {}).get("adj_close")
    last = price.get(run_session, {}).get("adj_close")
    expected = market_calendar[start_index : end_index + 1]
    valid_count = sum(1 for d in expected if price.get(d, {}).get("adj_close") is not None)
    if first is None or last is None:
        missing = start_date if first is None else run_session
        return _metric(None, "unavailable", f"Missing adjusted-close endpoint for {missing}", valid_count, run_session)
    if not first or not last or first <= 0:
        return _metric(None, "unavailable", "Invalid adjusted-close endpoint", valid_count, run_session)
    gaps = len(expected) - valid_count
    reason = f"Exact {n}-session endpoints; {valid_count}/{len(expected)} observations present"
    if gaps > 0:
        reason += f"; {gaps} interior session gap(s) disclosed"
    return _metric(float(last / first - 1.0), "valid", reason, valid_count, run_session)


def excess_metric(asset_return: dict[str, Any], benchmark_return: dict[str, Any]) -> dict[str, Any]:
    if asset_return.get("status") != "valid" or benchmark_return.get("status") != "valid":
        missing = []
        if asset_return.get("status") != "valid":
            missing.append("asset return unavailable")
        if benchmark_return.get("status") != "valid":
            missing.append("benchmark return unavailable")
        return _metric(None, "unavailable", "; ".join(missing), None, asset_return.get("session_date"))
    value = float(asset_return["value"] - benchmark_return["value"])
    return _metric(value, "valid", "Asset return minus benchmark return; displayed in percentage points", None, asset_return.get("session_date"))


def relative_wealth_change(asset_return: float, benchmark_return: float) -> float:
    return (1.0 + asset_return) / (1.0 + benchmark_return) - 1.0


def relative_state(excess21: float | None, excess63: float | None) -> str:
    if excess21 is None or excess63 is None:
        return "Unavailable"
    if excess21 == 0 or excess63 == 0:
        return "Mixed"
    if excess21 > 0 and excess63 > 0:
        return "Outperforming"
    if excess21 < 0 and excess63 < 0:
        return "Underperforming"
    if excess21 > 0 and excess63 < 0:
        return "Short-term outperformance / medium-term underperformance"
    return "Short-term underperformance / medium-term outperformance"


def split_adjusted_observations(chart: dict[str, Any]) -> list[dict[str, Any]]:
    """Recover contemporaneous raw close and share volume from split-adjusted Yahoo bars.

    Yahoo's chart close and volume are adjusted for later stock splits. For each
    observation, reversing the product of subsequent split ratios recovers raw
    close/volume. Their product should remain invariant through a split.
    """
    events = chart.get("events", {}).get("splits", {}) or {}
    splits: list[tuple[str, float]] = []
    for event in events.values():
        try:
            split_date = datetime.fromtimestamp(int(event["date"]), NY).date().isoformat()
            ratio = float(event["numerator"]) / float(event["denominator"])
            if ratio > 0:
                splits.append((split_date, ratio))
        except (KeyError, TypeError, ValueError, OSError):
            continue
    splits.sort()
    output = []
    for row in chart.get("observations", []):
        close = row.get("close")
        volume = row.get("volume")
        if close is None or volume is None:
            output.append({**row, "raw_close": None, "raw_volume": None, "dollar_volume_proxy": None})
            continue
        factor = prod(ratio for split_date, ratio in splits if row["date"] < split_date)
        raw_close = float(close) * factor
        raw_volume = float(volume) / factor
        output.append(
            {
                **row,
                "raw_close": raw_close,
                "raw_volume": raw_volume,
                "dollar_volume_proxy": raw_close * raw_volume,
            }
        )
    return output


def adv30_metric(chart: dict[str, Any], market_calendar: list[str], run_session: str, sessions: int = 30) -> dict[str, Any]:
    if run_session not in market_calendar:
        return _metric(None, "unavailable", "Run session is not in benchmark calendar", None, run_session)
    index = market_calendar.index(run_session)
    sessions = max(1, int(sessions))
    expected = market_calendar[max(0, index - (sessions - 1)) : index + 1]
    if len(expected) < sessions:
        return _metric(None, "unavailable", f"Fewer than {sessions} completed benchmark sessions", len(expected), run_session)
    rows = observation_map({**chart, "observations": split_adjusted_observations(chart)})
    values = [rows.get(d, {}).get("dollar_volume_proxy") for d in expected]
    valid = [value for value in values if value is not None and value >= 0]
    if len(valid) != sessions:
        return _metric(None, "unavailable", f"Requires all {sessions} raw close-volume pairs; {len(valid)}/{sessions} valid", len(valid), run_session)
    return _metric(sum(valid) / sessions, "valid", f"Mean of raw contemporaneous close multiplied by raw share volume over {sessions} sessions", sessions, run_session)


def _ema(values: list[float], period: int) -> list[float | None]:
    output: list[float | None] = [None] * len(values)
    if len(values) < period:
        return output
    seed = sum(values[:period]) / period
    output[period - 1] = seed
    alpha = 2.0 / (period + 1.0)
    previous = seed
    for index in range(period, len(values)):
        previous = values[index] * alpha + previous * (1.0 - alpha)
        output[index] = previous
    return output


def trend_metric(
    chart: dict[str, Any], market_calendar: list[str], run_session: str, settings: dict[str, Any]
) -> dict[str, Any]:
    if run_session not in market_calendar:
        return {"state": "Unavailable", "status": "unavailable", "reason": "Run session is not in the benchmark session calendar", "observations": 0, "session_date": run_session, "input_version": "yahoo-chart-close-ema-v1"}
    end = market_calendar.index(run_session)
    price_rows = observation_map(chart)
    prices = [price_rows.get(d, {}).get("close") for d in market_calendar[: end + 1]]
    last_gap = max((i for i, value in enumerate(prices) if value is None), default=-1)
    segment = prices[last_gap + 1 :]
    periods = tuple(int(value) for value in settings.get("ema_periods", (21, 50)))
    if len(periods) != 2:
        raise ValueError("ema_periods must contain the short and medium EMA windows")
    short_period, long_period = periods
    warmups = settings.get("ema_warmup_sessions", {})
    warm_short = int(warmups.get(str(short_period), settings.get(f"ema{short_period}_warmup_sessions", short_period * 4)))
    warm_long = int(warmups.get(str(long_period), settings.get(f"ema{long_period}_warmup_sessions", long_period * 4)))
    slope_sessions = int(settings.get("ema_slope_sessions", 5))
    warm_slope = warm_short + slope_sessions
    if len(segment) < warm_short:
        return {
            "state": "Unavailable",
            "status": "unavailable",
            "reason": f"Requires {warm_short} consecutive closes for EMA{short_period}; {len(segment)} available after the latest gap",
            f"ema{short_period}": None,
            f"ema{long_period}": None,
            f"ema{short_period}_slope_{slope_sessions}": None,
            "observations": len(segment),
            "session_date": run_session,
            "input_version": "yahoo-chart-close-ema-v1",
        }
    values = [float(value) for value in segment]
    eshort = _ema(values, short_period)
    elong = _ema(values, long_period)
    i = len(values) - 1
    if len(values) < warm_slope:
        return {
            "state": "Unavailable",
            "status": "unavailable",
            "reason": f"EMA{short_period} is available; requires {warm_slope} consecutive closes for its {slope_sessions}-session slope",
            f"ema{short_period}": eshort[i],
            f"ema{long_period}": None,
            f"ema{short_period}_slope_{slope_sessions}": None,
            "price_close": values[-1],
            "observations": len(values),
            "session_date": run_session,
            "input_version": "yahoo-chart-close-ema-v1",
        }
    slope = float(eshort[i] - eshort[i - slope_sessions])
    if len(values) < warm_long or elong[i] is None:
        return {
            "state": "Unavailable",
            "status": "unavailable",
            "reason": f"EMA{short_period} is available; requires {warm_long} consecutive closes for EMA{long_period} trend classification",
            f"ema{short_period}": eshort[i],
            f"ema{long_period}": None,
            f"ema{short_period}_slope_{slope_sessions}": slope,
            "price_close": values[-1],
            "observations": len(values),
            "session_date": run_session,
            "input_version": "yahoo-chart-close-ema-v1",
        }
    current = values[-1]
    if current > eshort[i] and eshort[i] > elong[i] and slope > 0:
        state = "Uptrend"
    elif current < eshort[i] and eshort[i] < elong[i] and slope < 0:
        state = "Downtrend"
    else:
        state = "Mixed"
    return {
        "state": state,
        "status": "valid",
        "reason": f"Consecutive closes; EMA{short_period} and EMA{long_period} use recursive smoothing seeded by a simple average",
        f"ema{short_period}": float(eshort[i]),
        f"ema{long_period}": float(elong[i]),
        f"ema{short_period}_slope_{slope_sessions}": slope,
        "price_close": current,
        "observations": len(values),
        "session_date": run_session,
        "input_version": "yahoo-chart-close-ema-v1",
    }


def breadth_metric(
    eligible: list[dict[str, Any]],
    value_key: str,
    review_complete: bool,
    membership_fresh: bool,
    settings: dict[str, Any],
) -> dict[str, Any]:
    valid = [row for row in eligible if row.get(value_key) is not None]
    eligible_count = len(eligible)
    valid_count = len(valid)
    coverage = valid_count / eligible_count if eligible_count else None
    above = sum(1 for row in valid if row.get("price_close", 0) > row[value_key])
    fraction = above / valid_count if valid_count else None
    reason = None
    label = "Unavailable"
    if not review_complete:
        reason = "Membership review is incomplete; reviewed-subset fraction only"
    elif not membership_fresh:
        reason = "Holdings snapshot is stale"
    elif valid_count < int(settings["minimum_breadth_sample"]):
        reason = f"Requires at least {settings['minimum_breadth_sample']} valid companies; {valid_count} valid"
    elif coverage is None or coverage < float(settings["minimum_breadth_coverage"]):
        reason = f"Requires at least {int(settings['minimum_breadth_coverage'] * 100)}% coverage; {valid_count}/{eligible_count} valid"
    elif fraction is not None:
        reason = None
        if fraction > 0.5:
            label = "Majority above EMA21"
        elif fraction < 0.5:
            label = "Majority below or at EMA21"
        else:
            label = "Half above EMA21"
    return {
        "above_count": above if valid_count else None,
        "valid_count": valid_count,
        "eligible_count": eligible_count,
        "coverage": coverage,
        "fraction": fraction,
        "label": label,
        "label_reason": reason,
        "reviewed_subset_only": not review_complete,
    }


def select_candidates(rows: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    """Cycle Liquid, Liquid, Strong, Weak without duplicate companies."""
    by_company: dict[str, dict[str, Any]] = {}
    for row in sorted(
        rows,
        key=lambda r: (
            -(r.get("adv30_usd") if r.get("adv30_usd") is not None else float("-inf")),
            -(r.get("etf_weight_pct") or 0.0),
            -(r.get("market_cap_usd") or 0.0),
            str(r.get("security_id") or r.get("ticker")),
        ),
    ):
        company_id = str(row.get("company_id") or row.get("security_id") or row.get("ticker"))
        by_company.setdefault(company_id, row)
    rows = list(by_company.values())
    liquid = sorted(
        rows,
        key=lambda r: (
            -(r.get("adv30_usd") if r.get("adv30_usd") is not None else float("-inf")),
            -(r.get("etf_weight_pct") or 0.0),
            -(r.get("market_cap_usd") or 0.0),
            str(r.get("security_id") or r.get("ticker")),
        ),
    )
    strong = sorted(
        [r for r in rows if r.get("excess21") is not None and r["excess21"] > 0],
        key=lambda r: (-r["excess21"], -(r.get("adv30_usd") or 0.0), str(r.get("security_id") or r.get("ticker"))),
    )
    weak = sorted(
        [r for r in rows if r.get("excess21") is not None and r["excess21"] < 0],
        key=lambda r: (r["excess21"], -(r.get("adv30_usd") or 0.0), str(r.get("security_id") or r.get("ticker"))),
    )
    queues = {"Liquid": liquid, "Strong": strong, "Weak": weak}
    ranks = {
        "Liquid": {r.get("ticker"): i + 1 for i, r in enumerate(liquid)},
        "Strong": {r.get("ticker"): i + 1 for i, r in enumerate(strong)},
        "Weak": {r.get("ticker"): i + 1 for i, r in enumerate(weak)},
    }
    pointers = {name: 0 for name in queues}
    chosen: list[dict[str, Any]] = []
    selected = set()
    cycle = ("Liquid", "Liquid", "Strong", "Weak")
    while len(chosen) < limit and len(selected) < len(rows):
        wanted = cycle[len(chosen) % len(cycle)]
        queue = queues[wanted]
        while pointers[wanted] < len(queue) and queue[pointers[wanted]].get("ticker") in selected:
            pointers[wanted] += 1
        chosen_row = None
        actual_queue = wanted
        if pointers[wanted] < len(queue):
            chosen_row = queue[pointers[wanted]]
            pointers[wanted] += 1
        else:
            actual_queue = "Liquid"
            while pointers["Liquid"] < len(liquid) and liquid[pointers["Liquid"]].get("ticker") in selected:
                pointers["Liquid"] += 1
            if pointers["Liquid"] < len(liquid):
                chosen_row = liquid[pointers["Liquid"]]
                pointers["Liquid"] += 1
        if chosen_row is None:
            break
        ticker = chosen_row.get("ticker")
        if ticker in selected:
            continue
        selected.add(ticker)
        chosen.append(
            {
                **chosen_row,
                "selection_slot": len(chosen) + 1,
                "selection_queue": actual_queue,
                "selection_queue_rank": ranks.get(actual_queue, {}).get(ticker),
                "selection_reason": (
                    f"Slot {len(chosen) + 1} from the {actual_queue} queue "
                    f"(queue rank {ranks.get(actual_queue, {}).get(ticker) or 'not ranked'}); "
                    "selection is a browsing convention, not a trading signal."
                ),
            }
        )
    return chosen


def breadth_label_from_fraction(
    above: int, valid: int, eligible: int, membership_fresh: bool, review_complete: bool,
    min_sample: int = 8, min_coverage: float = 0.8
) -> tuple[str, str | None]:
    if eligible == 0:
        return "Unavailable", "No eligible companies"
    if not membership_fresh:
        return "Unavailable", "Holdings snapshot is stale"
    if not review_complete:
        return "Unavailable", "Membership review is incomplete"
    if valid < min_sample:
        return "Unavailable", f"Requires {min_sample} valid companies"
    if valid / eligible < min_coverage:
        return "Unavailable", f"Coverage below {min_coverage:.0%}"
    if above * 2 > valid:
        return "Majority above EMA21", None
    if above * 2 < valid:
        return "Majority below or at EMA21", None
    return "Half above EMA21", None

