"""Collect source snapshots, apply eligibility rules, and build the dashboard data."""

from __future__ import annotations

import json
import math
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .metrics import (
    NY,
    adv30_metric,
    breadth_label_from_fraction,
    completed_session,
    excess_metric,
    observation_map,
    relative_state,
    return_metric,
    select_candidates,
    session_dates,
    split_adjusted_observations,
    trend_metric,
)
from .sources import fetch_holdings, fetch_nasdaq_summary, fetch_sec_latest_annual, fetch_yahoo_chart


WINDOWS = (5, 21, 63, 126)


def _numeric(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _metric_values(metrics: dict[str, Any]) -> dict[str, float | None]:
    return {str(window): metrics[str(window)].get("value") for window in WINDOWS}


def _fetch_many(
    symbols: set[str],
    fetcher: Any,
    workers: int = 4,
    request_interval_seconds: float = 0.0,
) -> tuple[dict[str, Any], dict[str, str]]:
    results: dict[str, Any] = {}
    errors: dict[str, str] = {}
    ordered_symbols = sorted(symbols)
    if workers <= 1:
        for index, symbol in enumerate(ordered_symbols):
            if index and request_interval_seconds > 0:
                time.sleep(request_interval_seconds)
            try:
                results[symbol] = fetcher(symbol)
            except Exception as exc:  # retain per-symbol failures as explicit unavailable data
                errors[symbol] = f"{type(exc).__name__}: {exc}"
        return results, errors
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = {pool.submit(fetcher, symbol): symbol for symbol in ordered_symbols}
        for future in as_completed(jobs):
            symbol = jobs[future]
            try:
                results[symbol] = future.result()
            except Exception as exc:  # retain per-symbol failures as explicit unavailable data
                errors[symbol] = f"{type(exc).__name__}: {exc}"
    return results, errors


def _returns(chart: dict[str, Any] | None, calendar: list[str], session: str | None) -> dict[str, dict[str, Any]]:
    if chart is None or session is None:
        return {
            str(n): {
                "value": None,
                "status": "unavailable",
                "reason": "Price source unavailable" if chart is None else "No verified completed session",
                "observation_count": None,
                "session_date": session,
                "input_version": "yahoo-chart-adjusted-close-v1",
            }
            for n in WINDOWS
        }
    return {str(n): return_metric(chart, calendar, session, n) for n in WINDOWS}


def _number_from_quote(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return None
    raw = str(value).strip().replace(",", "").replace("$", "")
    multiplier = 1.0
    if raw.endswith(("T", "B", "M", "K")):
        suffix = raw[-1]
        multiplier = {"T": 1e12, "B": 1e9, "M": 1e6, "K": 1e3}[suffix]
        raw = raw[:-1]
    try:
        return float(raw) * multiplier
    except ValueError:
        return None


def _holdings_map(holdings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    # Preserve the complete source list. If a provider repeats a share line,
    # aggregate its fund weight under the first row for the company key.
    result: dict[str, dict[str, Any]] = {}
    for row in holdings.get("rows", []):
        ticker = str(row.get("ticker") or "").strip()
        if not ticker:
            continue
        if ticker not in result:
            result[ticker] = dict(row)
        else:
            prior = _numeric(result[ticker].get("weight_pct")) or 0.0
            current = _numeric(row.get("weight_pct")) or 0.0
            result[ticker]["weight_pct"] = prior + current
    return result


def _breadth(eligible: list[dict[str, Any]], review_complete: bool, membership_fresh: bool, settings: dict[str, Any]) -> dict[str, Any]:
    def measure(name: str, predicate: Any, values: list[float] | None = None) -> dict[str, Any]:
        valid_rows = [row for row in eligible if predicate(row, "valid")]
        valid_count = len(valid_rows)
        denominator = len(eligible)
        count = sum(1 for row in valid_rows if predicate(row, "above"))
        value = count / valid_count if valid_count else None
        coverage = valid_count / denominator if denominator else None
        label, reason = breadth_label_from_fraction(
            count,
            valid_count,
            denominator,
            membership_fresh,
            review_complete,
            int(settings["minimum_breadth_sample"]),
            float(settings["minimum_breadth_coverage"]),
        ) if name == "above_ema21" else ("Not required", None)
        return {
            "name": name,
            "count": count if valid_count else None,
            "valid_count": valid_count,
            "eligible_count": denominator,
            "coverage": coverage,
            "fraction": value,
            "reviewed_unquantified_eligible_count": sum(1 for row in eligible if row.get("evidence_category") == "Reviewed, unquantified"),
            "reviewed_unquantified_valid_count": sum(1 for row in valid_rows if row.get("evidence_category") == "Reviewed, unquantified"),
            "label": label,
            "label_reason": reason,
            "reviewed_subset_only": not review_complete,
        }

    ema21 = measure("above_ema21", lambda row, mode: row.get("ema21") is not None and (mode == "valid" or row.get("price_close", 0) > row["ema21"]))
    ema50 = measure("above_ema50", lambda row, mode: row.get("ema50") is not None and (mode == "valid" or row.get("price_close", 0) > row["ema50"]))
    uptrend_rows = [row for row in eligible if row.get("trend") == "Uptrend"]
    trend_valid_count = sum(1 for row in eligible if row.get("trend_status") == "valid")
    return21 = [row["returns"]["21"]["value"] for row in eligible if row["returns"]["21"]["status"] == "valid"]
    return {
        "above_ema21": ema21,
        "above_ema50": ema50,
        "uptrend": {
            "count": len(uptrend_rows) if trend_valid_count else None,
            "valid_count": trend_valid_count,
            "eligible_count": len(eligible),
            "coverage": trend_valid_count / len(eligible) if eligible else None,
            "fraction": len(uptrend_rows) / trend_valid_count if trend_valid_count else None,
            "reviewed_unquantified_eligible_count": sum(1 for row in eligible if row.get("evidence_category") == "Reviewed, unquantified"),
            "reviewed_unquantified_valid_count": sum(1 for row in eligible if row.get("trend_status") == "valid" and row.get("evidence_category") == "Reviewed, unquantified"),
            "label": "Not required",
            "label_reason": None,
            "reviewed_subset_only": not review_complete,
        },
        "median_return21": {
            "value": statistics.median(return21) if return21 else None,
            "valid_count": len(return21),
            "eligible_count": len(eligible),
            "coverage": len(return21) / len(eligible) if eligible else None,
            "reviewed_unquantified_eligible_count": sum(1 for row in eligible if row.get("evidence_category") == "Reviewed, unquantified"),
            "reviewed_unquantified_valid_count": sum(1 for row in eligible if row["returns"]["21"]["status"] == "valid" and row.get("evidence_category") == "Reviewed, unquantified"),
            "status": "valid" if return21 else "unavailable",
            "reason": "Median of valid reviewed-subset Return21 values" if return21 else "No valid Return21 observations",
        },
    }


def _stock_row(
    theme: dict[str, Any], member: dict[str, Any], holding: dict[str, Any], chart: dict[str, Any] | None,
    quote: dict[str, Any] | None, anchor_chart: dict[str, Any] | None, spy_returns: dict[str, Any],
    calendar: list[str], session: str, settings: dict[str, Any], error: str | None,
) -> dict[str, Any]:
    ticker = member["ticker"]
    if chart is None:
        price_map: dict[str, dict[str, Any]] = {}
        raw_map: dict[str, dict[str, Any]] = {}
        returns = _returns(None, calendar, session)
        adv = {"value": None, "status": "unavailable", "reason": error or "Price source unavailable", "observation_count": 0, "session_date": session}
        trend = {"state": "Unavailable", "status": "unavailable", "reason": error or "Price source unavailable", "ema21": None, "ema50": None, "price_close": None}
        instrument = None
        price_currency = None
    else:
        price_map = observation_map(chart)
        raw_rows = split_adjusted_observations(chart)
        raw_map = {row["date"]: row for row in raw_rows}
        returns = _returns(chart, calendar, session)
        adv = adv30_metric(chart, calendar, session)
        trend = trend_metric(chart, calendar, session, settings)
        instrument = chart.get("meta", {}).get("instrumentType")
        price_currency = chart.get("meta", {}).get("currency")
    quote_exchange = str((quote or {}).get("exchange") or "")
    quote_industry = str((quote or {}).get("industry") or "")
    quote_sector = str((quote or {}).get("sector") or "")
    cap = _number_from_quote((quote or {}).get("market_cap_usd"))
    raw_close = _numeric(raw_map.get(session, {}).get("raw_close")) if chart is not None else None
    market_cap_freshness = "retrieved with current Nasdaq quote summary; provider does not expose a separate field timestamp" if quote else "unavailable"
    reasons: list[str] = []
    if quote is None:
        reasons.append("Market-cap and industry source unavailable")
    if not quote_exchange.startswith(("NYSE", "NASDAQ")):
        reasons.append("Listing exchange is not confirmed as NYSE or Nasdaq")
    if instrument != "EQUITY":
        reasons.append("Price source did not identify an equity instrument")
    if price_currency != "USD":
        reasons.append("Price currency is not confirmed as USD")
    if member.get("security_type") not in ("common_share", "sponsored_ADS"):
        reasons.append("Security type is outside the eligible stock set")
    evidence_check = member.get("_evidence_freshness", {})
    if evidence_check.get("status") != "current":
        reasons.append(evidence_check.get("reason") or "Latest annual-filing freshness check unavailable")
    if cap is None:
        reasons.append("Market capitalization is unavailable")
    elif cap < float(settings["market_cap_floor_usd"]):
        reasons.append(f"Market capitalization is below ${settings['market_cap_floor_usd'] / 1e9:.0f}B")
    if raw_close is None:
        reasons.append("Raw close is unavailable on the run session")
    elif raw_close < float(settings["raw_close_floor_usd"]):
        reasons.append(f"Raw close is below ${settings['raw_close_floor_usd']:.0f}")
    if adv.get("value") is None:
        reasons.append("ADV$30 is unavailable")
    elif adv["value"] < float(settings["adv30_floor_usd"]):
        reasons.append(f"ADV$30 is below ${settings['adv30_floor_usd'] / 1e6:.0f}M")
    if "biotechnolog" in quote_industry.lower() or "biotech" in quote_industry.lower():
        reasons.append("Industry is classified as biotechnology and is excluded by default")
    eligible = not reasons
    anchor_returns = _returns(anchor_chart, calendar, session)
    stock_excess = {str(n): excess_metric(returns[str(n)], anchor_returns[str(n)]) for n in WINDOWS}
    ex21 = stock_excess["21"].get("value") if stock_excess["21"].get("status") == "valid" else None
    ex63 = stock_excess["63"].get("value") if stock_excess["63"].get("status") == "valid" else None
    company_id = str(member.get("evidence", {}).get("cik") or ticker)
    return {
        "ticker": ticker,
        "company": holding.get("company") or member.get("company") or ticker,
        "company_id": company_id,
        "security_type": member.get("security_type"),
        "security_mapping_note": member.get("security_mapping_note"),
        "exchange": quote_exchange,
        "sector": quote_sector,
        "industry": quote_industry,
        "market_cap_usd": cap,
        "market_cap_status": "valid" if cap is not None else "unavailable",
        "market_cap_freshness": market_cap_freshness,
        "market_cap_retrieved_at": quote.get("retrieved_at") if quote else None,
        "market_cap_field_timestamp": None,
        "raw_close": raw_close,
        "raw_close_status": "valid" if raw_close is not None else "unavailable",
        "adv30_usd": adv.get("value"),
        "adv30_metric": adv,
        "returns": returns,
        "excess_returns": stock_excess,
        "excess21": ex21,
        "excess63": ex63,
        "relative_state": relative_state(ex21, ex63),
        "trend": trend.get("state", "Unavailable"),
        "trend_status": trend.get("status", "unavailable"),
        "trend_reason": trend.get("reason"),
        "ema21": trend.get("ema21"),
        "ema50": trend.get("ema50"),
        "ema21_slope_5": trend.get("ema21_slope_5"),
        "price_close": trend.get("price_close") or raw_close,
        "trend_observations": trend.get("observations"),
        "etf_weight_pct": _numeric(holding.get("weight_pct")),
        "eligibility": "eligible_provisional" if eligible else "excluded_or_unavailable",
        "eligibility_reasons": reasons,
        "evidence_category": member.get("category"),
        "evidence_note": member.get("review_note"),
        "evidence": member.get("evidence"),
        "evidence_freshness": evidence_check,
        "reviewed_date": member.get("reviewed_date"),
        "review_complete": False,
        "chart_source": chart.get("url") if chart else None,
        "quote_source": quote.get("url") if quote else None,
        "session_date": session,
        "input_version": "yahoo-chart-adjusted-close-v1",
    }


def _anchor_summary(theme: dict[str, Any], chart: dict[str, Any] | None, spy_chart: dict[str, Any] | None, calendar: list[str], session: str | None, settings: dict[str, Any], error: str | None) -> dict[str, Any]:
    returns = _returns(chart, calendar, session)
    trend = trend_metric(chart, calendar, session, settings) if chart else {"state": "Unavailable", "status": "unavailable", "reason": error or "Price source unavailable"}
    adv = adv30_metric(chart, calendar, session) if chart else {"value": None, "status": "unavailable", "reason": error or "Price source unavailable", "observation_count": 0}
    excess = {str(n): excess_metric(returns[str(n)], _returns(spy_chart, calendar, session)[str(n)]) for n in WINDOWS}
    ex21 = excess["21"].get("value") if excess["21"].get("status") == "valid" else None
    ex63 = excess["63"].get("value") if excess["63"].get("status") == "valid" else None
    observations = observation_map(chart) if chart else {}
    last_64 = calendar[max(0, len(calendar) - 64) :]
    consecutive64 = len(last_64) == 64 and all(observations.get(d, {}).get("close") is not None for d in last_64)
    meta = chart.get("meta", {}) if chart else {}
    instrument_ok = meta.get("instrumentType") == "ETF" and meta.get("currency") == "USD"
    history_ok = consecutive64 and len(calendar) >= 64
    volume_ok = adv.get("value") is not None and adv["value"] >= float(settings["anchor_adv30_floor_usd"])
    return {
        "ticker": theme["anchor"],
        "returns": returns,
        "excess_returns": excess,
        "relative_state": relative_state(ex21, ex63),
        "trend": trend.get("state", "Unavailable"),
        "trend_status": trend.get("status", "unavailable"),
        "trend_reason": trend.get("reason"),
        "ema21": trend.get("ema21"),
        "ema50": trend.get("ema50"),
        "ema21_slope_5": trend.get("ema21_slope_5"),
        "adv30_usd": adv.get("value"),
        "adv30_metric": adv,
        "history_observations": len([d for d in calendar if observations.get(d, {}).get("close") is not None]),
        "consecutive_64_sessions": consecutive64,
        "instrument_currency_valid": instrument_ok,
        "anchor_criteria": {
            "history_64_sessions": history_ok,
            "adv30_at_least_1m": volume_ok,
            "usd_unleveraged_equity_etf_mandate": instrument_ok and bool(theme.get("unleveraged_equity_etf_review")),
        },
        "anchor_screen_valid": history_ok and volume_ok and instrument_ok and bool(theme.get("unleveraged_equity_etf_review")),
        "unleveraged_equity_etf_review": bool(theme.get("unleveraged_equity_etf_review")),
        "mandate_review_note": theme.get("anchor_instrument_review"),
        "meta": {"currency": meta.get("currency"), "instrument_type": meta.get("instrumentType"), "exchange": meta.get("fullExchangeName")},
        "source_url": chart.get("url") if chart else None,
        "source_error": error,
        "session_date": session,
    }


def build_snapshot(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    theme_cfg = json.loads((root / "config/themes.json").read_text(encoding="utf-8"))
    evidence_cfg = json.loads((root / "config/evidence_reviews.json").read_text(encoding="utf-8"))
    comparison_cfg = json.loads((root / "config/anchor_comparisons.json").read_text(encoding="utf-8"))
    settings = theme_cfg["settings"]
    themes = theme_cfg["themes"]
    evidence_by_theme: dict[str, dict[str, dict[str, Any]]] = {}
    for member in evidence_cfg["members"]:
        evidence_by_theme.setdefault(member["theme_id"], {})[member["ticker"]] = member

    holdings: dict[str, Any] = {}
    holdings_errors: dict[str, str] = {}
    for theme in themes:
        try:
            holdings[theme["anchor"]] = fetch_holdings(theme)
        except Exception as exc:
            holdings_errors[theme["anchor"]] = f"{type(exc).__name__}: {exc}"
    comparisons: dict[str, Any] = {}
    for item in comparison_cfg["comparisons"]:
        pseudo = {
            "anchor": item["ticker"],
            "holdings_source": {"method": item["method"], "url": item["holdings_url"]},
        }
        try:
            comparisons[item["ticker"]] = fetch_holdings(pseudo)
        except Exception as exc:
            holdings_errors[item["ticker"]] = f"{type(exc).__name__}: {exc}"

    chart_symbols = set(theme_cfg.get("context_symbols", ["SPY", "QQQ"]))
    for theme in themes:
        chart_symbols.add(theme["anchor"])
        if theme.get("parent_sector"):
            chart_symbols.add(theme["parent_sector"])
        chart_symbols.update(
            ticker
            for ticker, member in evidence_by_theme.get(theme["id"], {}).items()
            if member.get("category") == "Core business"
        )
    chart_symbols.update(item["ticker"] for item in comparison_cfg["comparisons"])
    # Yahoo throttles bursts of chart requests. Keep these sequential with a
    # short pause so a normal on-demand run is less likely to receive HTTP 429.
    print(f"Collecting {len(chart_symbols)} price histories sequentially (1.5s pacing).", flush=True)
    charts, chart_errors = _fetch_many(
        chart_symbols, fetch_yahoo_chart, workers=1, request_interval_seconds=1.5
    )

    print(f"Price histories: {len(charts)} retrieved, {len(chart_errors)} unavailable. Checking quote and filing sources.", flush=True)
    member_symbols = {
        ticker
        for entries in evidence_by_theme.values()
        for ticker, member in entries.items()
        if member.get("category") == "Core business"
    }
    # Industry-only review of XBI: non-stock identifiers remain unmapped, never guessed.
    industry_symbols = {row['ticker'] for row in holdings.get('XBI', {}).get('rows', []) if row.get('ticker', '').isalpha()}
    quotes, quote_errors = _fetch_many(member_symbols | industry_symbols, fetch_nasdaq_summary, workers=2)

    ciks = {
        str(member.get("evidence", {}).get("cik"))
        for entries in evidence_by_theme.values()
        for member in entries.values()
        if member.get("category") == "Core business" and member.get("evidence", {}).get("cik")
    }
    sec_latest, sec_errors = _fetch_many(ciks, fetch_sec_latest_annual, workers=4)
    sec_freshness: dict[str, dict[str, Any]] = {}
    for entries in evidence_by_theme.values():
        for ticker, member in entries.items():
            evidence = member.get("evidence", {})
            cik = str(evidence.get("cik") or "")
            checked = sec_latest.get(cik)
            if checked is None:
                if member.get("category") != "Core business":
                    sec_freshness[f"{member['theme_id']}:{ticker}"] = {
                        "status": "not_checked",
                        "reason": "Evidence remains unresolved; annual-filing freshness was not checked for stock eligibility.",
                        "checked_at": None,
                    }
                    continue
                reason = sec_errors.get(cik, "SEC annual-filing check returned no result") if cik else "Evidence record has no SEC CIK"
                sec_freshness[f"{member['theme_id']}:{ticker}"] = {"status": "unavailable", "reason": reason, "checked_at": None}
                continue
            evidence_date = str(evidence.get("filed_date") or "")
            latest_date = str(checked.get("latest_annual_filed_date") or "")
            if latest_date and evidence_date and latest_date <= evidence_date:
                sec_freshness[f"{member['theme_id']}:{ticker}"] = {
                    "status": "current",
                    "reason": "No later 10-K, 20-F, or 40-F was found in the SEC submissions feed.",
                    "checked_at": checked.get("retrieved_at"),
                    "latest_annual_form": checked.get("latest_annual_form"),
                    "latest_annual_filed_date": latest_date,
                    "source_url": checked.get("url"),
                    "latest_filing_url": checked.get("filing_url"),
                }
            else:
                sec_freshness[f"{member['theme_id']}:{ticker}"] = {
                    "status": "stale",
                    "reason": f"A later annual filing is available ({checked.get('latest_annual_form')} filed {latest_date}); business evidence needs review.",
                    "checked_at": checked.get("retrieved_at"),
                    "latest_annual_form": checked.get("latest_annual_form"),
                    "latest_annual_filed_date": latest_date,
                    "source_url": checked.get("url"),
                    "latest_filing_url": checked.get("filing_url"),
                }

    now = datetime.now(timezone.utc)
    spy_chart = charts.get("SPY")
    calendar_source_symbol = next(
        (symbol for symbol in ["SPY", "QQQ"] + [theme["anchor"] for theme in themes] if charts.get(symbol)),
        None,
    )
    calendar_source_chart = charts.get(calendar_source_symbol) if calendar_source_symbol else None
    run_session = completed_session(calendar_source_chart, now) if calendar_source_chart else None
    calendar = [d for d in session_dates(calendar_source_chart) if run_session and d <= run_session] if calendar_source_chart else []
    run_date = now.astimezone(NY).date().isoformat()
    spy_returns = _returns(spy_chart, calendar, run_session)
    raw_inputs = {
        "retrieved_at": now.isoformat(timespec="seconds"),
        "session_calendar": calendar,
        "calendar_source_symbol": calendar_source_symbol,
        "charts": charts,
        "quotes": quotes,
        "holdings": holdings,
        "comparison_holdings": comparisons,
        "sec_annual_checks": sec_latest,
        "errors": {"charts": chart_errors, "quotes": quote_errors, "holdings": holdings_errors, "sec": sec_errors},
    }

    context = []
    for symbol in theme_cfg.get("context_symbols", ["SPY", "QQQ"]):
        chart = charts.get(symbol)
        returns = _returns(chart, calendar, run_session)
        trend = trend_metric(chart, calendar, run_session, settings) if chart else {"state": "Unavailable", "status": "unavailable", "reason": chart_errors.get(symbol, "Price source unavailable")}
        context.append({
            "ticker": symbol,
            "returns": returns,
            "trend": trend.get("state", "Unavailable"),
            "trend_status": trend.get("status", "unavailable"),
            "trend_reason": trend.get("reason"),
            "source_url": chart.get("url") if chart else None,
            "meta": {"currency": chart.get("meta", {}).get("currency"), "instrument_type": chart.get("meta", {}).get("instrumentType")} if chart else {},
        })

    theme_results = []
    review_theme_cfg = evidence_cfg.get("themes", {})
    for theme in themes:
        anchor = theme["anchor"]
        anchor_chart = charts.get(anchor)
        source_holdings = holdings.get(anchor, {"as_of": None, "url": theme["holdings_source"]["url"], "rows": []})
        holdings_rows = source_holdings.get("rows", [])
        holdings_lookup = _holdings_map(source_holdings)
        holdings_as_of = source_holdings.get("as_of")
        try:
            holdings_age = (date.fromisoformat(run_date) - date.fromisoformat(holdings_as_of)).days if holdings_as_of else None
        except ValueError:
            holdings_age = None
        holdings_fresh = holdings_age is not None and 0 <= holdings_age <= int(settings["maximum_holdings_age_days"])
        anchor_summary = _anchor_summary(theme, anchor_chart, spy_chart, calendar, run_session, settings, chart_errors.get(anchor))

        member_records = evidence_by_theme.get(theme["id"], {})
        member_rows: list[dict[str, Any]] = []
        pending: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []
        for ticker, held in holdings_lookup.items():
            member = member_records.get(ticker)
            industry_quote = quotes.get(ticker) if theme['id'] == 'biotechnology' else None
            if industry_quote and 'biotech' in str(industry_quote.get('industry', '')).lower():
                excluded.append({**held, 'reasons': ['Industry classified as biotechnology; excluded by the default stock-universe rule'], 'industry': industry_quote.get('industry'), 'source_url': industry_quote.get('url'), 'retrieved_at': industry_quote.get('retrieved_at')})
                continue
            if member is None:
                pending.append({**held, "status": "Pending evidence review", "reason": "Non-stock or unmapped holding identifier; no ticker mapping invented." if not ticker.isalpha() and theme["id"] == "biotechnology" else "Current official holding has no completed issuer business-evidence review."})
                continue
            if member.get("category") != "Core business":
                pending.append({
                    **held,
                    "status": "Unresolved",
                    "reason": member.get("review_note") or "Business relevance remains unresolved.",
                    "evidence_category": member.get("category"),
                    "evidence": member.get("evidence"),
                    "reviewed_date": member.get("reviewed_date"),
                })
                continue
            member = dict(member)
            member["_evidence_freshness"] = sec_freshness.get(f"{theme['id']}:{ticker}", {"status": "unavailable", "reason": "SEC annual-filing freshness check unavailable"})
            row = _stock_row(
                theme, member, held, charts.get(ticker), quotes.get(ticker), anchor_chart, spy_returns,
                calendar, run_session, settings, chart_errors.get(ticker) or quote_errors.get(ticker),
            )
            member_rows.append(row)
            if row["eligibility"] != "eligible_provisional":
                excluded.append({"ticker": ticker, "company": row["company"], "reasons": row["eligibility_reasons"], "weight_pct": row["etf_weight_pct"], "evidence": row.get("evidence"), "evidence_freshness": row.get("evidence_freshness")})

        # Evidence records whose ticker is no longer present in the official snapshot are not current members.
        for ticker, member in member_records.items():
            if ticker not in holdings_lookup:
                excluded.append({"ticker": ticker, "company": member.get("company", ticker), "reasons": ["Official holdings retrieval unavailable; membership cannot be determined" if anchor in holdings_errors else "Not present in the retrieved current official holdings snapshot"], "weight_pct": None, "evidence": member.get("evidence")})

        eligible = [row for row in member_rows if row["eligibility"] == "eligible_provisional"]
        # Deduplicate company identifiers. Keep the security with highest ADV$30 and aggregate fund weights.
        by_company: dict[str, list[dict[str, Any]]] = {}
        for row in eligible:
            by_company.setdefault(row["company_id"], []).append(row)
        eligible_companies = []
        for company_rows in by_company.values():
            company_rows.sort(key=lambda row: (-(row.get("adv30_usd") or 0.0), row["ticker"]))
            chosen = dict(company_rows[0])
            chosen["share_classes"] = [row["ticker"] for row in company_rows]
            chosen["etf_weight_pct"] = sum(row.get("etf_weight_pct") or 0.0 for row in company_rows)
            eligible_companies.append(chosen)
        for row in eligible_companies:
            row["anchor"] = anchor
            row["theme_id"] = theme["id"]
        selected = select_candidates(eligible_companies, int(settings["max_candidates"]))
        breadth = _breadth(eligible_companies, bool(review_theme_cfg.get(theme["id"], {}).get("review_complete", False)), holdings_fresh, settings)
        weight = lambda rows: sum(row.get("etf_weight_pct") or 0.0 for row in rows)
        weight_by_issuer: dict[str, float] = {}
        for ticker, held in holdings_lookup.items():
            member = member_records.get(ticker, {})
            issuer_key = str((member.get("evidence") or {}).get("cik") or f"ticker:{ticker}")
            held_weight = _numeric(held.get("weight_pct"))
            if held_weight is not None:
                weight_by_issuer[issuer_key] = weight_by_issuer.get(issuer_key, 0.0) + held_weight
        top_weights = sorted(weight_by_issuer.values(), reverse=True)
        theme_returns = anchor_summary["returns"]
        theme_excess = anchor_summary["excess_returns"]
        parent_summary = None
        parent_ticker = theme.get("parent_sector")
        if parent_ticker:
            parent_chart = charts.get(parent_ticker)
            parent_returns = _returns(parent_chart, calendar, run_session)
            parent_trend = trend_metric(parent_chart, calendar, run_session, settings) if parent_chart else {"state": "Unavailable", "status": "unavailable", "reason": chart_errors.get(parent_ticker, "Price source unavailable")}
            parent_summary = {
                "ticker": parent_ticker,
                "returns": parent_returns,
                "excess_returns": {str(n): excess_metric(parent_returns[str(n)], theme_returns[str(n)]) for n in WINDOWS},
                "trend": parent_trend.get("state", "Unavailable"),
                "trend_status": parent_trend.get("status", "unavailable"),
                "trend_reason": parent_trend.get("reason"),
                "source_url": parent_chart.get("url") if parent_chart else None,
                "source_error": chart_errors.get(parent_ticker),
            }
        representation_status = "ETF-only" if not eligible_companies else ("Limited stock coverage" if len(eligible_companies) < 8 else "Provisional stock coverage")
        theme_results.append({
            "id": theme["id"],
            "name": theme["name"],
            "scope": theme["scope"],
            "included": theme["included"],
            "excluded": theme["excluded"],
            "anchor": anchor,
            "anchor_rationale": theme["anchor_rationale"],
            "anchor_url": theme["anchor_url"],
            "parent_sector": theme.get("parent_sector"),
            "representation_limit": theme.get("representation_limit"),
            "representation_status": representation_status,
            "holdings_source": {"provider": theme["holdings_source"]["provider"], "url": source_holdings.get("url"), "as_of": holdings_as_of, "publication_date": None, "retrieved_at": source_holdings.get("retrieved_at")},
            "holdings_age_days": holdings_age,
            "holdings_fresh": holdings_fresh,
            "holdings_status": "current" if holdings_fresh else ("stale" if holdings_as_of else "unavailable"),
            "official_holdings_count": len(holdings_rows),
            "official_unique_ticker_count": len(holdings_lookup),
            "duplicate_holding_ticker_rows": len(holdings_rows) - len(holdings_lookup),
            "evidence_reviewed_holdings_count": sum(1 for ticker in holdings_lookup if ticker in member_records and member_records[ticker].get("category") == "Core business"),
            "reviewed_data_count": len(member_rows),
            "eligible_reviewed_count": len(eligible_companies),
            "pending_count": len(pending),
            "excluded_count": len(excluded),
            "review_complete": bool(review_theme_cfg.get(theme["id"], {}).get("review_complete", False)),
            "review_reason": review_theme_cfg.get(theme["id"], {}).get("reason"),
            "evidence_freshness_check_count": sum(1 for ticker, member in member_records.items() if member.get("category") == "Core business" and f"{theme['id']}:{ticker}" in sec_freshness),
            "stale_evidence_count": sum(1 for ticker, member in member_records.items() if member.get("category") == "Core business" and sec_freshness.get(f"{theme['id']}:{ticker}", {}).get("status") == "stale"),
            "unavailable_evidence_freshness_count": sum(1 for ticker, member in member_records.items() if member.get("category") == "Core business" and sec_freshness.get(f"{theme['id']}:{ticker}", {}).get("status") == "unavailable"),
            "unresolved_evidence_count": sum(1 for row in pending if row.get("status") == "Unresolved"),
            "pending_evidence_count": sum(1 for row in pending if row.get("status") == "Pending evidence review"),
            "anchor_screen": anchor_summary,
            "parent_comparison": parent_summary,
            "returns": theme_returns,
            "excess_returns": theme_excess,
            "relative_state": anchor_summary["relative_state"],
            "trend": anchor_summary["trend"],
            "trend_status": anchor_summary["trend_status"],
            "trend_reason": anchor_summary["trend_reason"],
            "breadth": breadth,
            "eligible_weight_pct": weight(eligible_companies),
            "selected_weight_pct": weight(selected),
            "visible15_weight_pct": weight(selected[: int(settings["compact_candidates"])]),
            "largest_holding_weight_pct": top_weights[0] if top_weights else None,
            "top5_holding_weight_pct": sum(top_weights[:5]) if top_weights else None,
            "concentration_note": "Duplicate ticker lines are aggregated; reviewed share classes are combined by SEC CIK. Unreviewed share-class aliases remain separate because company mapping is incomplete.",
            "selected": selected,
            "reviewed_universe": eligible_companies,
            "pending_holdings": pending,
            "exclusions": excluded,
            "all_holdings": holdings_rows,
            "source_error": holdings_errors.get(anchor) or chart_errors.get(anchor),
            "session_date": run_session,
        })

    comparison_results = []
    for item in comparison_cfg["comparisons"]:
        symbol = item["ticker"]
        chart = charts.get(symbol)
        comp_hold = comparisons.get(symbol, {"as_of": None, "rows": []})
        ret = _returns(chart, calendar, run_session)
        exc = {str(n): excess_metric(ret[str(n)], spy_returns[str(n)]) for n in WINDOWS}
        adv = adv30_metric(chart, calendar, run_session) if chart else {"value": None, "status": "unavailable", "reason": chart_errors.get(symbol, "Price source unavailable")}
        weights = sorted([_numeric(row.get("weight_pct")) for row in comp_hold.get("rows", []) if _numeric(row.get("weight_pct")) is not None], reverse=True)
        comparison_results.append({
            **item,
            "holdings_as_of": comp_hold.get("as_of"),
            "holdings_count": len(comp_hold.get("rows", [])),
            "returns": ret,
            "excess_returns": exc,
            "adv30_usd": adv.get("value"),
            "top5_weight_pct": sum(weights[:5]) if weights else None,
            "holdings_weight_sum_pct": sum(weights) if weights else None,
            "source_error": holdings_errors.get(symbol) or chart_errors.get(symbol),
        })

    for theme in theme_results:
        theme["anchor_comparisons"] = [row for row in comparison_results if row["theme_id"] == theme["id"]]

    snapshot = {
        "schema_version": "1.0",
        "run_id": now.strftime("themescope-%Y%m%dT%H%M%SZ"),
        "generated_at": now.isoformat(timespec="seconds"),
        "run_date": run_date,
        "session_date": run_session,
        "timezone": "America/New_York",
        "registry_version": theme_cfg["registry_version"],
        "evidence_review_date": evidence_cfg["review_date"],
        "settings": settings,
        "benchmark": "SPY",
        "session_calendar_source": calendar_source_symbol,
        "benchmark_status": "valid" if spy_chart else "unavailable",
        "context": context,
        "themes": theme_results,
        "comparisons": comparison_results,
        "sources": {
            "price_provider": "Yahoo Finance chart endpoint; adjusted close plus corporate-action events",
            "quote_provider": "Nasdaq quote summary; market-cap field has no separate field timestamp",
            "evidence_provider": "SEC EDGAR latest annual filings cited in config/evidence_reviews.json",
            "evidence_freshness_provider": "SEC EDGAR submissions; latest annual 10-K/20-F/40-F date rechecked during each run",
            "source_errors": {"charts": chart_errors, "quotes": quote_errors, "holdings": holdings_errors, "sec": sec_errors},
            "partial": bool(chart_errors or quote_errors or holdings_errors or sec_errors),
        },
        "limitations": [
            "Yahoo Finance chart is an accessible but undocumented endpoint; its adjusted-close semantics and publication behavior are vendor conventions, not an exchange feed guarantee.",
            "Before 16:30 America/New_York, the current-day bar is treated as incomplete; this run uses the prior session. After 16:30, today's bar is used only when the provider's regular-market timestamp is on that session date.",
            "Nasdaq market-cap and industry summaries do not expose per-field observation timestamps; retrieval time is recorded and these eligibility inputs are provisional.",
            "Issuer business evidence uses the latest annual SEC filing retrieved for each reviewed ticker. Newer material disclosures are not exhaustively screened; theme membership review is incomplete.",
            "Each run rechecks the SEC submissions feed for a later annual filing. A newer annual form makes that issuer ineligible until evidence is reviewed; an unavailable check also prevents provisional selection. This check does not classify subsequent 8-K disclosures.",
            "Only the provisional reviewed subset is used for stock selection. It is not the full current eligible universe, so breadth labels are suppressed and raw subset fractions are selection-biased.",
            "No historical point-in-time membership, prediction, trade signal, or performance validation is represented."
        ],
    }
    raw_inputs["run_session"] = run_session
    raw_inputs["evidence_freshness"] = sec_freshness
    raw_inputs["retrieval_error_count"] = len(chart_errors) + len(quote_errors) + len(holdings_errors) + len(sec_errors)
    return snapshot, raw_inputs

