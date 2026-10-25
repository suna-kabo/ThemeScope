"""Stable theme membership and watchlist-based breadth calculations."""

from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path
from typing import Any

from .metrics import adv30_metric, observation_map, return_metric, trend_metric


WATCHLIST_VERSION = 1


def validate_watchlists(config: dict[str, Any], capacity: int = 20) -> dict[str, dict[str, Any]]:
    """Validate human-maintained many-to-many membership records."""
    records: dict[str, dict[str, Any]] = {}
    for record in config.get("watchlists", []):
        theme_id = str(record.get("theme_id") or "").strip()
        anchor = str(record.get("anchor") or "").strip().upper()
        if not theme_id or not anchor:
            raise ValueError("Each watchlist requires theme_id and anchor")
        if theme_id in records:
            raise ValueError(f"Duplicate watchlist for {theme_id}")
        members = record.get("members")
        if not isinstance(members, list):
            raise ValueError(f"{theme_id}: members must be a list")
        if len(members) > capacity:
            raise ValueError(f"{theme_id}: {len(members)} members exceeds capacity {capacity}")
        seen: set[str] = set()
        clean = []
        for member in members:
            ticker = str(member.get("ticker") or "").strip().upper()
            relationship = str(member.get("relationship") or "").strip().title()
            reason = str(member.get("reason") or "").strip()
            if not ticker or ticker in seen:
                raise ValueError(f"{theme_id}: missing or duplicate ticker {ticker!r}")
            if relationship not in {"Core", "Related"}:
                raise ValueError(f"{theme_id}/{ticker}: relationship must be Core or Related")
            if not reason:
                raise ValueError(f"{theme_id}/{ticker}: a short reason is required")
            seen.add(ticker)
            clean.append({**member, "ticker": ticker, "relationship": relationship, "reason": reason})
        records[theme_id] = {**record, "theme_id": theme_id, "anchor": anchor, "members": clean}
    return records


def read_watchlists(path: Path, capacity: int = 20) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    config = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"version": WATCHLIST_VERSION, "watchlists": []}
    return config, validate_watchlists(config, capacity)


def _breadth_metric(
    members: list[dict[str, Any]], charts: dict[str, Any], calendar: list[str],
    session: str | None, period: int, settings: dict[str, Any],
) -> dict[str, Any]:
    configured = len(members)
    above = valid = 0
    for member in members:
        chart = charts.get(member["ticker"])
        if not chart:
            continue
        close = observation_map(chart).get(session, {}).get("close") if session else None
        trend = trend_metric(chart, calendar, session, settings) if session else {}
        ema = trend.get(f"ema{period}")
        if isinstance(close, (int, float)) and math.isfinite(close) and isinstance(ema, (int, float)) and math.isfinite(ema):
            valid += 1
            above += int(close > ema)
    value = 100.0 * above / valid if valid else None
    minimum = int(settings.get("minimum_breadth_sample", 8))
    coverage_floor = float(settings.get("minimum_breadth_coverage", 0.8))
    coverage = valid / configured if configured else 0.0
    reason = None
    code = None
    if not configured:
        reason, code = "Watchlist is not configured.", "not_configured"
    elif valid < minimum:
        reason, code = "Fewer than 8 members have valid price history.", "too_few_valid_members"
    elif coverage < coverage_floor:
        reason, code = "Valid price data are available for fewer than 80% of configured members.", "price_coverage_low"
    return {
        "value": value if reason is None else None,
        "status": "valid" if reason is None else "unavailable",
        "reason": reason,
        "reason_code": code,
        "above_count": above,
        "valid_count": valid,
        "eligible_count": configured,
        "configured_count": configured,
        "coverage_pct": 100 * coverage if configured else None,
        "session_date": session,
        "ema_period": period,
        "method": "Configured theme watchlist members above close EMA / members with valid close and EMA",
    }


def _at_session(calendar: list[str], session: str | None, offset: int) -> str | None:
    if not session or session not in calendar:
        return None
    i = calendar.index(session) - offset
    return calendar[i] if i >= 0 else None


def _stock_row(theme: dict[str, Any], member: dict[str, Any], charts: dict[str, Any], calendar: list[str], session: str | None, settings: dict[str, Any], anchor_chart: dict[str, Any], market_caps: dict[str, Any]) -> dict[str, Any]:
    ticker = member["ticker"]
    chart = charts.get(ticker)
    rows = observation_map(chart) if chart else {}
    close = rows.get(session, {}).get("close") if session else None
    trend = trend_metric(chart, calendar, session, settings) if chart and session else {}
    returns = {str(n): return_metric(chart, calendar, session, n) if chart and session else {"value": None, "status": "unavailable", "reason": "No price history"} for n in (5, 21, 63)}
    adv = adv30_metric(chart, calendar, session, int(settings.get("adv30_sessions", 30))) if chart and session else {"value": None, "status": "unavailable"}
    benchmark = {str(n): return_metric(anchor_chart, calendar, session, n) if anchor_chart and session else {"value": None, "status": "unavailable"} for n in (5, 21, 63)}
    excess = {n: {"value": returns[n].get("value") - benchmark[n].get("value") if returns[n].get("status") == benchmark[n].get("status") == "valid" else None, "status": "valid" if returns[n].get("status") == benchmark[n].get("status") == "valid" else "unavailable"} for n in returns}
    return {
        **member,
        "ticker": ticker,
        "company": member.get("company") or ticker,
        "membership_tag": member["relationship"],
        "membership_rationale": member["reason"],
        "membership_source": "Configured theme watchlist",
        "reviewed_date": member.get("reviewed_date"),
        "theme_id": theme["id"],
        "theme_name": theme["name"],
        "anchor": theme["anchor"],
        "price_close": close,
        "adv30_usd": adv.get("value"),
        "market_cap_usd": (market_caps.get(ticker) or {}).get("market_cap_usd"),
        "market_cap_retrieved_at": (market_caps.get(ticker) or {}).get("retrieved_at"),
        "ema21": trend.get("ema21"),
        "ema50": trend.get("ema50"),
        "above_ema21": close > trend["ema21"] if close is not None and trend.get("ema21") is not None else None,
        "above_ema50": close > trend["ema50"] if close is not None and trend.get("ema50") is not None else None,
        "trend": trend.get("state", "Unavailable"),
        "returns": returns,
        "excess_returns": excess,
        "session_date": session,
        "price_status": "valid" if close is not None else "unavailable",
        "price_reason": None if close is not None else "No close observation for the selected market session",
        "selection_slot": 1 + next(i for i, row in enumerate(theme.get("_members", [])) if row["ticker"] == ticker),
        "selection_queue": member["relationship"],
    }


def apply_watchlists(snapshot: dict[str, Any], raw: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Attach configured stocks and calculate EMA breadth without affecting scores."""
    settings = snapshot.get("settings", {})
    capacity = int(settings.get("watchlist_capacity", 20))
    records = validate_watchlists(config, capacity)
    charts = {**raw.get("charts", {}), **raw.get("v5", {}).get("charts", {}), **raw.get("v5", {}).get("iwm_breadth_charts", {})}
    market_caps = raw.get("market_cap_cache", {})
    calendar = raw.get("session_calendar", [])
    session = snapshot.get("session_date")
    for theme in snapshot.get("themes", []):
        record = records.get(theme["id"])
        members = record.get("members", []) if record and record.get("anchor") == theme.get("anchor") else []
        # Keep the full configured list independent of the visible 15/20 row limit.
        theme["watchlist_reviewed_date"] = record.get("reviewed_date") if record else None
        theme["reviewed_candidate_count"] = record.get("reviewed_candidate_count") if record else None
        theme["watchlist_list_rationale"] = record.get("list_rationale") if record else None
        theme["configured_watchlist_count"] = len(members)
        configured_status = record.get("status") if record else None
        theme["watchlist_status"] = configured_status or ("configured" if record else "not_configured")
        theme["watchlist_exception_reason"] = record.get("exception_reason") if record else None
        theme["watchlist_unavailable_reason"] = None if record else "Theme watchlist is not configured."
        theme["selected"] = []
        theme["_members"] = members
        anchor_chart = charts.get(theme.get("anchor"), {})
        for member in members[:capacity]:
            theme["selected"].append(_stock_row(theme, member, charts, calendar, session, settings, anchor_chart, market_caps))
        breadth = {}
        for period in (21, 50):
            current = _breadth_metric(members, charts, calendar, session, period, settings)
            prior_session = _at_session(calendar, session, 5)
            prior = _breadth_metric(members, charts, calendar, prior_session, period, settings) if prior_session else {"status": "unavailable", "reason": "The five-session-prior observation is unavailable.", "reason_code": "historical_observation_missing", "value": None, "valid_count": 0, "above_count": 0, "configured_count": len(members), "eligible_count": len(members)}
            change = current["value"] - prior["value"] if current["status"] == prior.get("status") == "valid" else None
            if current["status"] == "valid" and prior.get("status") != "valid":
                current["change_reason"] = "The five-session-prior observation is unavailable."
            current.update({"t_minus_5": prior.get("value"), "change_5_pp": change, "prior_session": prior_session, "prior": prior})
            breadth[str(period)] = current
            theme[f"theme_breadth{period}_pct"] = current["value"]
            theme[f"theme_breadth{period}_above"] = current["above_count"]
            theme[f"theme_breadth{period}_valid"] = current["valid_count"]
            theme[f"theme_breadth{period}_change_5_pp"] = change
            theme[f"theme_breadth{period}_t_minus_5"] = prior.get("value")
            # Transitional internal aliases are removed by the v7 compact
            # snapshot and export projections.
            theme[f"etf_breadth{period}_pct"] = current["value"]
            theme[f"breadth_valid_ema{period}_count"] = current["valid_count"]
            theme[f"breadth{period}_change_5_pp"] = change
            theme[f"breadth{period}_t_minus_5"] = prior.get("value")
        theme["theme_watchlist_breadth"] = breadth
        theme["has_watchlist"] = bool(members)
        theme["watchlist_member_count"] = len(members)
        theme["stock_scope"] = "Configured watchlist" if members else "Reviewed ETF-only" if configured_status == "reviewed_etf_only" else "ETF only"
        if members:
            theme["stock_drilldown_status"] = "available"
        elif configured_status == "reviewed_etf_only":
            theme["stock_drilldown_status"] = "reviewed_etf_only"
            theme["watchlist_unavailable_reason"] = record.get("exception_reason")
        else:
            theme["stock_drilldown_status"] = "not_configured"
        for legacy_key in (
            "holdings_breadth", "holdings_asof", "breadth_eligible_equity_count",
            "has_curated_watchlist", "curated_watchlist_count", "stock_audit",
            "reviewed_universe", "pending_holdings", "exclusions", "sector_member_exclusions",
        ):
            theme.pop(legacy_key, None)
        theme["field_status"] = theme.setdefault("field_status", {})
        for period in (21, 50):
            metric = breadth[str(period)]
            theme["field_status"][f"theme_breadth{period}_pct"] = metric
            theme["field_status"][f"theme_breadth{period}_change_5_pp"] = {
                "value": metric.get("change_5_pp"),
                "status": "valid" if metric.get("change_5_pp") is not None else "unavailable",
                "reason": metric.get("change_reason") or (None if metric.get("change_5_pp") is not None else "Current and five-session-prior theme-watchlist breadth must both be valid."),
                "session_date": session,
                "prior_session": metric.get("prior_session"),
            }
            theme[f"breadth_status_{period}"] = metric["status"]
            theme[f"breadth_unavailable_reason_{period}"] = metric.get("reason")
        theme.pop("_members", None)
    snapshot["watchlist_version"] = config.get("version", WATCHLIST_VERSION)
    snapshot["watchlist_reviewed_dates"] = sorted({record.get("reviewed_date") for record in records.values() if record.get("reviewed_date")})
    return snapshot


def propose_import(csv_path: Path, config: dict[str, Any], themes: list[dict[str, Any]], filters: dict[str, Any]) -> dict[str, Any]:
    """Read a TradingView export and produce review-only candidates/diffs."""
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("TradingView CSV has no data rows")
    # TradingView uses a typographic multiplication sign in some exports and
    # ASCII x in others; normalize the header while preserving the source key.
    fields = {str(key).strip().casefold().replace("×", "x"): key for key in rows[0]}
    symbol_key = next((fields[key] for key in ("ticker", "symbol", "name") if key in fields), None)
    if symbol_key is None:
        raise ValueError("TradingView CSV needs a Ticker, Symbol, or Name column")
    price_key = next((fields[k] for k in ("price", "close") if k in fields), None)
    adv_key = next((fields[k] for k in ("adv30", "average dollar volume", "avg dollar volume", "price x average volume over 30 days", "price x average volume, 30 days", "price * average volume over 30 days", "30-day average dollar volume") if k in fields), None)
    volume_key = next((fields[k] for k in ("average volume", "avg volume", "volume") if k in fields), None)
    cap_key = next((fields[k] for k in ("market capitalization", "market cap", "market_cap_usd") if k in fields), None)
    # Sector and Industry describe the business; neither is a theme assignment.
    theme_key = next((fields[k] for k in ("theme_id", "theme") if k in fields), None)
    industry_key, sector_key = fields.get("industry"), fields.get("sector")
    description_key = next((fields[k] for k in ("description", "company", "company name") if k in fields), None)
    exchange_key = fields.get("exchange")
    def number(row, key):
        if not key: return None
        value = str(row.get(key, "")).replace(",", "").replace("$", "").strip().upper()
        match = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*([KMB])?\s*", value)
        if not match:
            return None
        amount = float(match.group(1))
        return amount * {None: 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[match.group(2)]
    minimum_price = float(filters.get("raw_close_floor_usd", 15))
    minimum_adv = float(filters.get("adv30_floor_usd", 20_000_000))
    minimum_cap = float(filters.get("market_cap_floor_usd", 2_000_000_000))
    strict = bool(filters.get("require_complete_maintenance_data"))
    if strict and (price_key is None or adv_key is None or cap_key is None or exchange_key is None or description_key is None):
        raise ValueError("Maintenance CSV must contain Symbol, Description, Price, Market capitalization, Price x average volume over 30 days, and Exchange columns")
    market_cap_cache = filters.get("market_cap_cache", {})
    existing = validate_watchlists(config, int(filters.get("watchlist_capacity", 20)))
    theme_lookup = {}
    for theme in themes:
        for alias in (theme.get("id"), theme.get("name"), theme.get("anchor")):
            if alias:
                theme_lookup[str(alias).strip().casefold()] = theme
    proposals = []
    rejected = []
    accepted_by_theme: dict[str, set[str]] = {}
    seen_tickers: set[str] = set()
    for row in rows:
        ticker = str(row.get(symbol_key) or "").strip().upper().split(":")[-1]
        if not ticker: continue
        if ticker in seen_tickers:
            raise ValueError(f"TradingView CSV contains duplicate ticker {ticker}")
        seen_tickers.add(ticker)
        price, volume, cap = number(row, price_key), number(row, volume_key), number(row, cap_key)
        cap_source = "scanner CSV" if cap is not None else None
        if cap is None and isinstance(market_cap_cache.get(ticker), dict):
            cap = number({"value": market_cap_cache[ticker].get("market_cap_usd")}, "value")
            cap_source = "maintained local cache" if cap is not None else None
        adv = number(row, adv_key)
        if adv is None and volume is not None and price is not None and not strict:
            adv = volume * price
        reasons = []
        if price is None and strict: reasons.append("price missing")
        elif price is not None and price < minimum_price: reasons.append(f"price below ${minimum_price:g}")
        if adv is None and strict: reasons.append("ADV30 missing")
        elif adv is not None and adv < minimum_adv: reasons.append(f"ADV estimate below ${minimum_adv:,.0f}")
        if cap is None and strict: reasons.append("market cap missing")
        elif cap is not None and cap < minimum_cap: reasons.append(f"market cap below ${minimum_cap:,.0f}")
        exchange = str(row.get(exchange_key) or "").strip() if exchange_key else ""
        if strict and not exchange.upper().startswith(("NYSE", "NASDAQ")):
            reasons.append("not listed on NYSE or Nasdaq")
        if reasons:
            rejected.append({"ticker": ticker, "reasons": reasons})
            continue
        assigned = theme_lookup.get(str(row.get(theme_key) or "").strip().casefold()) if theme_key else None
        memberships = []
        if assigned:
            item = existing.get(assigned.get("id"), {})
            current = {member["ticker"] for member in item.get("members", [])}
            accepted_by_theme.setdefault(assigned["id"], set()).add(ticker)
            if ticker not in current:
                memberships.append({"theme_id": assigned["id"], "name": assigned.get("name"), "anchor": item.get("anchor") or assigned.get("anchor"), "suggested_relationship": "Related", "change": "proposed_add"})
        checks = {
            "price": "passed" if price is not None else "not provided; review required",
            "adv30": "passed" if adv is not None and adv >= minimum_adv else "not provided; review required" if adv is None else "failed",
            "market_cap": "passed (" + str(cap_source) + ")" if cap is not None and cap >= minimum_cap else "not provided; review required" if cap is None else "failed (" + str(cap_source) + ")",
            "history_63_and_ema50": "not verified by scanner CSV; review required",
        }
        proposal = {
            "ticker": ticker,
            "company": row.get(description_key) if description_key else ticker,
            "exchange": exchange,
            "instrument_type": "operating_company" if strict else None,
            "industry": row.get(industry_key) if industry_key else None,
            "sector": row.get(sector_key) if sector_key else None,
            "price": price,
            "adv30_estimate_usd": adv,
            "market_cap_usd": cap,
            "maintenance": {
                "date": filters.get("maintenance_date"),
                "source_type": "tradingview_universe",
                "price_usd": price,
                "market_cap_usd": cap,
                "adv30_usd": adv,
                "adjusted_price_sessions": None,
            },
            "matched_theme": assigned.get("id") if assigned else None,
            "proposed_memberships": memberships,
            "filter_checks": checks,
            "review_required": True,
        }
        proposals.append(proposal)
    diffs = []
    if theme_key:
        for theme_id, imported in accepted_by_theme.items():
            current = {member["ticker"] for member in existing.get(theme_id, {}).get("members", [])}
            diffs.append({"theme_id": theme_id, "proposed_additions": sorted(imported - current), "proposed_removals": sorted(current - imported)})
    return {
        "input_file": csv_path.name,
        "input_rows": len(rows),
        "proposed_count": len(proposals),
        "rejected_count": len(rejected),
        "theme_column": theme_key,
        "theme_assignment_required": theme_key is None,
        "proposals": proposals,
        "rejected": rejected,
        "theme_diffs": diffs,
        "existing_memberships": sum(len(item["members"]) for item in existing.values()),
        "auto_overwrite": False,
    }


def build_reviewed_config(
    proposal: dict[str, Any],
    review: dict[str, Any],
    themes: list[dict[str, Any]],
    active_anchors: dict[str, str],
) -> dict[str, Any]:
    """Apply a completed human assignment map to candidate maintenance facts."""
    candidate_by_ticker = {row["ticker"]: row for row in proposal.get("proposals", [])}
    review_rows = review.get("themes", [])
    review_by_id: dict[str, list[dict[str, Any]]] = {}
    for row in review_rows:
        review_by_id.setdefault(str(row.get("theme_id") or ""), []).append(row)
    expected_ids = set(active_anchors)
    if set(review_by_id) != expected_ids or any(len(rows) != 1 for rows in review_by_id.values()):
        missing = sorted(expected_ids - set(review_by_id))
        unknown = sorted(set(review_by_id) - expected_ids)
        raise ValueError(f"Review map must contain each active theme exactly once; missing={missing}, unknown={unknown}")
    theme_by_id = {row.get("id"): row for row in themes}
    records = []
    for theme_id in sorted(expected_ids):
        entry = review_by_id[theme_id][0]
        theme = theme_by_id.get(theme_id, {})
        members = []
        for assigned in entry.get("members", []):
            ticker = str(assigned.get("ticker") or "").strip().upper()
            candidate = candidate_by_ticker.get(ticker)
            maintenance = dict(assigned.get("maintenance") or (candidate or {}).get("maintenance") or {})
            if not ticker or not maintenance:
                raise ValueError(f"{theme_id}: {ticker or '(blank)'} has no candidate and maintained eligibility facts")
            maintenance.setdefault("date", review.get("reviewed_date"))
            if maintenance.get("source_type") not in {"anchor_etf", "tradingview_universe", "outside_etf_addition"}:
                raise ValueError(f"{theme_id}/{ticker}: candidate source must be anchor_etf, tradingview_universe, or outside_etf_addition")
            members.append({
                "ticker": ticker,
                "company": assigned.get("company") or (candidate or {}).get("company"),
                "exchange": assigned.get("exchange") or (candidate or {}).get("exchange"),
                "instrument_type": assigned.get("instrument_type") or (candidate or {}).get("instrument_type"),
                "relationship": assigned.get("relationship"),
                "reason": assigned.get("reason"),
                "reviewed_date": review.get("reviewed_date"),
                "maintenance": maintenance,
                **{
                    key: assigned[key]
                    for key in ("source_url", "reason_source_url")
                    if assigned.get(key)
                },
            })
        records.append({
            "theme_id": theme_id,
            "anchor": active_anchors[theme_id],
            "status": entry.get("status"),
            "reviewed_date": review.get("reviewed_date"),
            "reviewed_candidate_count": entry.get("reviewed_candidate_count"),
            "exception_reason": entry.get("exception_reason"),
            "list_rationale": entry.get("list_rationale"),
            "members": members,
        })
    return {"version": 2, "reviewed_date": review.get("reviewed_date"), "watchlists": records}
