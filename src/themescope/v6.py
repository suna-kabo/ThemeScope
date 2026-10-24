"""v6 registry eligibility, snapshot contract, and source diagnostics."""

from __future__ import annotations

from datetime import date
from typing import Any
from urllib.parse import urlparse

from .metrics import adv30_metric, observation_map
from .ranking import average_ranks


def _valid_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _source_status(raw: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    errors = raw.get("errors", {})
    chart_errors = errors.get("charts", {})
    holdings_errors = errors.get("holdings", {})
    v5_errors = raw.get("v5", {}).get("chart_errors", {})
    iwm_errors = raw.get("v5", {}).get("iwm_breadth_errors", {})
    iwm_diagnostics = raw.get("v5", {}).get("iwm_breadth_diagnostics", {})
    iwm_shortfalls = iwm_diagnostics.get("history_shortfalls", {})
    charts = raw.get("charts", {})
    holdings = raw.get("holdings", {})
    context_holdings = raw.get("context_holdings", {})
    quotes = raw.get("quotes", {})
    v5 = raw.get("v5", {})
    indexes = v5.get("index_universes", {})
    mapped = v5.get("mapped_universes", {})
    diagnostics = snapshot.get("registry_diagnostics", [])
    registry_candidates = [candidate for exposure in diagnostics for candidate in exposure.get("candidates", [])]
    configured_holdings_candidates = sum(bool(candidate.get("holdings_source_configured")) for candidate in registry_candidates)
    return {
        "prices": {
            "provider": "Yahoo Finance chart API",
            "status": "unavailable" if not charts else "partial" if chart_errors else "available",
            "retrieved_at": raw.get("retrieved_at"),
            "effective_date": snapshot.get("session_date"),
            "unavailable_reason": ("No price histories retrieved" if not charts else f"{len(chart_errors)} requested price histories unavailable" if chart_errors else None),
            "errors": chart_errors,
            "datasets": {symbol: {"status": "available", "url": chart.get("url"), "retrieved_at": chart.get("retrieved_at"), "effective_date": (chart.get("observations") or [{}])[-1].get("date"), "unavailable_reason": None} for symbol, chart in charts.items()},
        },
        "holdings": {
            "provider": "Official ETF issuers",
            "status": "unavailable" if not holdings and not context_holdings else "partial" if holdings_errors or configured_holdings_candidates < len(registry_candidates) else "available",
            "retrieved_at": max((r.get("retrieved_at", "") for r in [*holdings.values(), *context_holdings.values()]), default=None),
            "effective_date": None,
            "unavailable_reason": ("No official holdings files retrieved" if not holdings and not context_holdings else f"Official holdings configured for {configured_holdings_candidates} of {len(registry_candidates)} ETF candidates; {len(holdings_errors)} retrieval errors" if holdings_errors or configured_holdings_candidates < len(registry_candidates) else None),
            "errors": holdings_errors,
            "configured_candidate_count": configured_holdings_candidates,
            "registry_candidate_count": len(registry_candidates),
            "datasets": {symbol: {"status": "available", "url": item.get("url"), "retrieved_at": item.get("retrieved_at"), "effective_date": item.get("as_of"), "unavailable_reason": None} for symbol, item in {**holdings, **context_holdings}.items()},
        },
        "index_constituents": {
            "provider": "S&P 500 classification table, Nasdaq-100 constituent list, and iShares IWM holdings",
            "status": "available" if indexes or context_holdings else "unavailable",
            "retrieved_at": max((r.get("retrieved_at", "") for r in [*indexes.values(), *context_holdings.values()]), default=None),
            "effective_date": None,
            "unavailable_reason": None if indexes or context_holdings else "Index constituent sources unavailable",
            "errors": {},
            "datasets": {symbol: {"status": "available", "url": item.get("url"), "retrieved_at": item.get("retrieved_at"), "date_semantics": item.get("date_semantics", "effective"), "observation_date": item.get("observation_date"), "effective_date": item.get("effective_date") or (item.get("as_of") if item.get("date_semantics") != "observation" else None), "unavailable_reason": None} for symbol, item in {**indexes, **context_holdings}.items()},
        },
        "volatility": {
            "provider": "Yahoo Finance chart API",
            "status": "available" if raw.get("charts", {}).get("^VIX") else "unavailable",
            "retrieved_at": raw.get("charts", {}).get("^VIX", {}).get("retrieved_at"),
            "effective_date": snapshot.get("session_date"),
            "unavailable_reason": raw.get("errors", {}).get("charts", {}).get("^VIX") if not raw.get("charts", {}).get("^VIX") else None,
            "url": raw.get("charts", {}).get("^VIX", {}).get("url"),
        },
        "market_cap": {
            "provider": "Nasdaq quote summary",
            "status": "unavailable" if not quotes else "partial" if errors.get("quotes") else "available",
            "retrieved_at": max((r.get("retrieved_at", "") for r in quotes.values()), default=None),
            "effective_date": None,
            "unavailable_reason": None if quotes else "No quote summaries retrieved",
            "errors": errors.get("quotes", {}),
            "datasets": {symbol: {"status": "available", "url": item.get("url"), "retrieved_at": item.get("retrieved_at"), "effective_date": item.get("effective_date"), "unavailable_reason": None} for symbol, item in quotes.items()},
        },
        "sec_annual_filing_checks": {
            "provider": "SEC EDGAR submissions",
            "status": "partial" if raw.get("errors", {}).get("sec") else "available" if raw.get("sec_annual_checks") else "unavailable",
            "retrieved_at": max((item.get("retrieved_at", "") for item in raw.get("sec_annual_checks", {}).values()), default=None),
            "effective_date": None,
            "unavailable_reason": "SEC annual filing checks were not retrieved" if not raw.get("sec_annual_checks") else None,
            "errors": raw.get("errors", {}).get("sec", {}),
            "datasets": {cik: {"status": "available", "url": item.get("url"), "retrieved_at": item.get("retrieved_at"), "effective_date": item.get("latest_annual_filed_date"), "unavailable_reason": None} for cik, item in raw.get("sec_annual_checks", {}).items()},
        },
        "aum": {"provider": None, "status": "unavailable", "retrieved_at": None, "effective_date": None, "unavailable_reason": "No reproducible ETF AUM source is configured."},
        "bid_ask_spread": {"provider": None, "status": "unavailable", "retrieved_at": None, "effective_date": None, "unavailable_reason": "No reproducible historical ETF bid/ask source is configured."},
        "breadth_histories": {
            "provider": "Yahoo Finance chart API",
            "status": "unavailable" if not indexes and not context_holdings else "partial" if v5_errors or iwm_errors or iwm_shortfalls else "available",
            "retrieved_at": raw.get("retrieved_at"),
            "effective_date": snapshot.get("session_date"),
            "unavailable_reason": ("Index/holdings constituent universes were not retrieved" if not indexes and not context_holdings else f"{len(v5_errors)} constituent histories; {len(iwm_errors)} IWM retrieval failures; {len(iwm_shortfalls)} IWM histories below warmup" if v5_errors or iwm_errors or iwm_shortfalls else None),
            "errors": {**v5_errors, **{"IWM:" + key: value for key, value in iwm_errors.items()}},
            "mapped_universes": {key: len(value.get("companies", [])) for key, value in mapped.items()},
            "iwm_diagnostics": iwm_diagnostics,
        },
    }


def _candidate_status(
    record: dict[str, Any], ticker: str, raw: dict[str, Any],
    snapshot: dict[str, Any], settings: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    breadth_reasons: list[str] = []
    session = snapshot.get("session_date")
    chart = raw.get("charts", {}).get(ticker)
    if not chart:
        reasons.append("ETF price history unavailable")
    observations = observation_map(chart) if chart else {}
    valid_history = sum(1 for d, row in observations.items() if (not session or d <= session) and _valid_number(row.get("close")))
    history_min = int(settings.get("anchor_minimum_history_sessions", 64))
    if valid_history < history_min:
        reasons.append(f"Requires {history_min} valid price sessions; {valid_history} available")
    meta = (chart or {}).get("meta", {})
    if meta.get("instrumentType") != "ETF" or meta.get("currency") != "USD":
        reasons.append("Retrieved instrument is not verified as a USD ETF")
    mandate_review = (record.get("candidate_reviews") or {}).get(ticker)
    if not mandate_review and record.get("anchor") == ticker and record.get("unleveraged_equity_etf_review"):
        mandate_review = {
            "status": "reviewed",
            "reviewed_date": record.get("mandate_review_date"),
            "source_url": record.get("anchor_url"),
            "rationale": record.get("anchor_instrument_review"),
        }
    review_url = urlparse(str((mandate_review or {}).get("source_url", "")))
    review_date = (mandate_review or {}).get("reviewed_date")
    try:
        date.fromisoformat(str(review_date))
        review_date_valid = True
    except ValueError:
        review_date_valid = False
    review_outcome = (mandate_review or {}).get("status")
    review_complete = bool(
        mandate_review
        and review_outcome in {"reviewed", "rejected"}
        and review_date_valid
        and review_url.scheme == "https"
        and review_url.netloc
        and mandate_review.get("rationale")
    )
    if not review_complete:
        reasons.append("ETF mandate review is incomplete: dated issuer source and rationale are required")
    elif review_outcome == "rejected":
        reasons.append("ETF mandate review rejected: " + str(mandate_review["rationale"]))

    adv = adv30_metric(chart, raw.get("session_calendar", []), session, int(settings.get("adv30_sessions", 30))) if chart and session else {"value": None, "reason": "No session-aligned volume history"}
    adv_value = adv.get("value")
    adv_floor = float(settings.get("anchor_adv30_floor_usd", 10_000_000))
    if not _valid_number(adv_value):
        reasons.append("30-session average dollar volume unavailable")
    elif adv_value < adv_floor:
        reasons.append(f"30-session average dollar volume ${adv_value:,.0f} is below ${adv_floor:,.0f}")

    holdings_configured = record.get("anchor") == ticker and bool(record.get("holdings_source"))
    holdings = raw.get("holdings", {}).get(ticker) if holdings_configured else None
    source_date = (holdings or {}).get("as_of")
    if not holdings_configured:
        breadth_reasons.append("Official holdings source is not configured for this ETF.")
    elif ticker in raw.get("errors", {}).get("holdings", {}):
        breadth_reasons.append("Holdings source retrieval failed for this run.")
        # A retained source object must never mask a current-run retrieval error.
        holdings = None
        source_date = None
    elif not holdings or not holdings.get("rows"):
        breadth_reasons.append("No eligible equity holdings were obtained from the configured source.")
    ref_date = session or snapshot.get("requested_asof") or snapshot.get("run_date")
    age = None
    if holdings_configured and holdings and holdings.get("rows") and not breadth_reasons:
        try:
            age = (date.fromisoformat(ref_date) - date.fromisoformat(source_date)).days
        except (TypeError, ValueError):
            breadth_reasons.append("Holdings effective date is unavailable or invalid.")
        if age is not None and age < 0:
            breadth_reasons.append("Holdings effective date is after the selected market session.")
        elif age is not None and age > int(settings.get("maximum_holdings_age_days", 35)):
            breadth_reasons.append("Holdings are older than the configured freshness limit.")

    mapped = raw.get("v5", {}).get("mapped_universes", {}).get(ticker, {}) if holdings_configured else {}
    breadth_count = len(mapped.get("companies", []))
    mapped_source_count = len((holdings or {}).get("rows", []))
    chart_attempts = raw.get("errors", {}).get("charts", {})
    chart_error = chart_attempts.get(ticker)
    if chart_error:
        reasons.append("Price retrieval error: " + str(chart_error))
    priority = list(record.get("candidate_anchors", [])).index(ticker)

    return {
        "ticker": ticker,
        "candidate_priority": priority + 1,
        "status": "eligible" if not reasons else "ineligible",
        "reasons": reasons,
        "breadth_status": "breadth_not_configured" if not holdings_configured else "breadth_temporarily_unavailable" if ticker in raw.get("errors", {}).get("holdings", {}) else "breadth_supported",
        "breadth_reasons": breadth_reasons,
        "breadth_diagnostics": {
            "source_row_count": mapped_source_count,
            "mapped_equity_count": breadth_count,
            "unresolved_mapping_count": len(mapped.get("unresolved_mappings", [])),
            "holdings_age_days": age,
            "holdings_effective_date": source_date,
            "retrieval_error": raw.get("errors", {}).get("holdings", {}).get(ticker),
        },
        "adv30_usd": adv_value,
        "adv30_status": adv.get("status", "unavailable"),
        "minimum_adv30_usd": adv_floor,
        "valid_history_sessions": valid_history,
        "minimum_history_sessions": history_min,
        "instrument_type": meta.get("instrumentType"),
        "mandate_review_status": review_outcome if review_complete else "incomplete",
        "mandate_review_complete": review_complete,
        "mandate_review_date": mandate_review.get("reviewed_date") if mandate_review else None,
        "mandate_review_source": mandate_review.get("source_url") if mandate_review else None,
        "mandate_review_source_filed_date": mandate_review.get("source_filed_date") if mandate_review else None,
        "mandate_review_rationale": mandate_review.get("rationale") if mandate_review else None,
        "currency": meta.get("currency"),
        "fund_name": meta.get("longName") or meta.get("shortName"),
        "exchange": meta.get("fullExchangeName") or meta.get("exchangeName"),
        "listing_status": "Active price history observed; listing status is not independently certified" if chart and valid_history >= history_min else "unavailable",
        "history_status": "passes minimum" if valid_history >= history_min else "below minimum or unavailable",
        "holdings_effective_date": source_date,
        "holdings_retrieved_at": (holdings or {}).get("retrieved_at"),
        "holdings_source_configured": holdings_configured,
        "mapped_equity_holdings": breadth_count,
        "source_holdings_rows": mapped_source_count,
        "unresolved_equity_mappings": len(mapped.get("unresolved_mappings", [])),
        "aum_status": "Unavailable: no configured reproducible ETF AUM source.",
        "aum_usd": None,
        "median_spread_pct": None,
        "spread_status": "Unavailable: no configured reproducible bid/ask history source.",
        "price_source_url": chart.get("url") if chart else None,
        "price_retrieved_at": chart.get("retrieved_at") if chart else None,
        "price_effective_date": session if chart and session in observations else ((chart.get("observations") or [{}])[-1].get("date") if chart else None),
    }


def _field_snapshot(row: dict[str, Any], session: str | None) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    values = {
        "price_close": row.get("price_close"),
        "ema21": row.get("ema21"),
        "ema50": row.get("ema50"),
        "return5": row.get("returns", {}).get("5", {}).get("value"),
        "return21": row.get("returns", {}).get("21", {}).get("value"),
        "return63": row.get("returns", {}).get("63", {}).get("value"),
        "excess21": row.get("excess_returns", {}).get("21", {}).get("value"),
        "excess63": row.get("excess_returns", {}).get("63", {}).get("value"),
        "current_strength": row.get("current_strength_score"),
        "medium_strength": row.get("medium_strength_score"),
        "theme_score": row.get("theme_score"),
        "breadth21": row.get("etf_breadth21_pct"),
        "breadth50": row.get("etf_breadth50_pct"),
        "price_vs_ema21_pct": row.get("price_vs_ema21_pct"),
        "price_vs_ema50_pct": row.get("price_vs_ema50_pct"),
        "breadth21_t_minus_5": row.get("breadth21_t_minus_5"),
        "breadth50_t_minus_5": row.get("breadth50_t_minus_5"),
        "breadth21_change_5_pp": row.get("breadth21_change_5_pp"),
        "breadth50_change_5_pp": row.get("breadth50_change_5_pp"),
    }
    statuses = row.get("field_status", {})
    for name, value in values.items():
        source_name = {
            "current_strength": "current_strength_score",
            "medium_strength": "medium_strength_score",
            "theme_score": "theme_score",
        }.get(name, name)
        metric = statuses.get(source_name, {})
        if name.startswith("return"):
            window = name.removeprefix("return")
            metric = row.get("returns", {}).get(window, {})
        elif name.startswith("excess"):
            window = name.removeprefix("excess")
            metric = row.get("excess_returns", {}).get(window, {})
        elif name == "breadth21":
            metric = row.get("field_status", {}).get("etf_breadth21_pct", {})
        elif name == "breadth50":
            metric = row.get("field_status", {}).get("etf_breadth50_pct", {})
        fields[name] = {
            "value": value,
            "observation_date": metric.get("session_date") or session,
            "status": metric.get("status") or ("valid" if _valid_number(value) else "unavailable"),
            "unavailable_reason": metric.get("reason") if not _valid_number(value) else None,
        }
    return fields


def _populate_sector_watchlists(
    snapshot: dict[str, Any], raw: dict[str, Any], registry: dict[str, Any]
) -> None:
    """Curate sector stocks from official fund holdings intersected with sourced GICS rows."""
    from .collect import _stock_row
    from .metrics import select_candidates

    inputs = raw.get("v5", {})
    mapped = inputs.get("mapped_universes", {})
    index_companies = mapped.get("SPY", {}).get("companies", [])
    index_by_cik = {str(row.get("company_id")): row for row in index_companies}
    source = inputs.get("index_universes", {}).get("SPY", {})
    source_url = source.get("url")
    charts = {**raw.get("charts", {}), **inputs.get("charts", {})}
    calendar = raw.get("session_calendar", [])
    session = snapshot.get("session_date")
    settings = snapshot.get("settings", {})
    spy_returns = next((row.get("returns", {}) for row in snapshot.get("context", []) if row.get("ticker") == "SPY"), {})
    records = {row.get("id"): row for row in registry.get("themes", [])}

    for exposure in snapshot.get("themes", []):
        if exposure.get("level") != "Sector":
            continue
        record = records.get(exposure.get("id"), {})
        holdings = raw.get("holdings", {}).get(exposure.get("anchor"), {})
        mapped_holdings = mapped.get(exposure.get("anchor"), {}).get("companies", [])
        holdings_source = holdings.get("url") or record.get("holdings_source", {}).get("url")
        index_name = record.get("name")
        source_rows = {str(row.get("ticker")): row for row in holdings.get("rows", [])}
        members = []
        excluded = []
        seen_ciks = set()
        for held_company in mapped_holdings:
            cik = str(held_company.get("company_id") or "")
            classified = index_by_cik.get(cik)
            if not classified or classified.get("sector") != index_name:
                continue
            symbols = held_company.get("symbols") or []
            if not symbols:
                excluded.append({"company": held_company.get("company"), "reason": "No SEC-verified US listing symbol"})
                continue
            ticker = sorted(symbols)[0]
            if cik in seen_ciks:
                continue
            seen_ciks.add(cik)
            source_holdings = [source_rows.get(str(ticker_)) for ticker_ in held_company.get("source_tickers", [])]
            source_holdings = [item for item in source_holdings if item]
            weights = [item.get("weight_pct") for item in source_holdings if _valid_number(item.get("weight_pct"))]
            held = {
                "ticker": ticker,
                "company": held_company.get("company") or classified.get("company") or ticker,
                "weight_pct": sum(value for value in weights if value is not None) if any(value is not None for value in weights) else None,
                "_is_anchor_holding": True,
            }
            rationale = (
                f"The current S&P 500 source classifies this issuer in {index_name}; "
                f"it also appears in the official {exposure.get('anchor')} holdings dated {holdings.get('as_of') or 'unknown'}. "
                "This supports sector membership, not a complete analysis of every business line."
            )
            member = {
                "ticker": ticker,
                "company": held["company"],
                "membership_tag": "Core",
                "membership_source": "; ".join(url for url in (holdings_source, source_url) if url),
                "membership_rationale": rationale,
                "security_type": "common_share",
                "security_mapping_note": "SEC CIK listing map; S&P 500 constituent and official sector-fund holdings intersection.",
                "category": "Sourced sector constituent",
                "review_note": "Sector tag derived from the current S&P 500 classification source and official ETF inclusion.",
                "evidence": {"cik": cik, "url": source_url},
                "reviewed_date": holdings.get("as_of") or source.get("as_of"),
                "requires_filing_review": False,
                "_evidence_freshness": {"status": "not_required", "reason": "Sector classification and ETF membership are sourced directly."},
            }
            chart = charts.get(ticker)
            quote_keys = [ticker, *held_company.get("source_tickers", [])]
            quote_keys.extend(value.replace("-", ".") for value in list(quote_keys) if "-" in value)
            quote = next((raw.get("quotes", {}).get(key) for key in quote_keys if raw.get("quotes", {}).get(key)), None)
            stock = _stock_row(
                record, member, held, chart, quote, charts.get(exposure.get("anchor")), spy_returns,
                calendar, session, settings, raw.get("errors", {}).get("charts", {}).get(ticker) or raw.get("errors", {}).get("quotes", {}).get(ticker) or inputs.get("chart_errors", {}).get(ticker),
            )
            members.append(stock)

        eligible = [row for row in members if row.get("eligibility") == "eligible_provisional"]
        selected = select_candidates(eligible, int(settings.get("watchlist_capacity", 20)))
        selected_by_ticker = {row.get("ticker"): row for row in selected}
        for row in members:
            choice = selected_by_ticker.get(row.get("ticker"))
            if choice:
                for key in ("selection_slot", "selection_queue", "selection_queue_rank", "selection_reason"):
                    row[key] = choice.get(key)
        for row in selected:
            row["anchor"] = exposure.get("anchor")
            row["theme_id"] = exposure.get("id")
            row["theme_name"] = exposure.get("name")
        exposure["reviewed_universe"] = eligible
        exposure["selected"] = selected
        exposure["eligible_reviewed_count"] = len(eligible)
        exposure["reviewed_data_count"] = len(members)
        exposure["excluded_count"] = len(excluded) + sum(row.get("eligibility") != "eligible_provisional" for row in members)
        exposure["sector_member_exclusions"] = excluded
        exposure["stock_audit"] = members
        exposure["stock_membership_configured"] = bool(records.get(exposure.get("id"), {}).get("holdings_source"))
        exposure["stock_membership_count"] = len(members)
        exposure["stock_collection_failure_count"] = int(
            bool(raw.get("errors", {}).get("holdings", {}).get(exposure.get("anchor")))
            or not holdings.get("rows")
            or not index_companies
        )
        exposure["stock_drilldown_status"] = (
            "available" if selected else
            "retrieval_failed" if exposure["stock_collection_failure_count"] else
            "no_eligible" if exposure["stock_membership_configured"] else
            "not_configured"
        )
        exposure["sector_membership_basis"] = {
            "index_source": source,
            "holdings_effective_date": holdings.get("as_of"),
            "method": "Current S&P 500 sector classification intersected with the official sector ETF equity holdings; stock filters and Liquid, Liquid, Strong, Weak selection then apply.",
            "scope_limit": "S&P 500 constituents present in the selected sector ETF; not every listed company in the sector.",
        }
        exposure["representation_status"] = "S&P 500 and official sector ETF holdings intersection" if selected else "No stock passed sourced membership and eligibility checks"


def _select_anchor(record: dict[str, Any], candidates: list[dict[str, Any]], current_anchor: str | None = None) -> str | None:
    eligible = [item for item in candidates if item.get("status") == "eligible"]
    if current_anchor and any(item.get("ticker") == current_anchor for item in eligible):
        return current_anchor
    if not eligible:
        return None

    def selection_key(candidate: dict[str, Any]) -> tuple[Any, ...]:
        ticker = candidate["ticker"]
        return (
            0 if ticker == record.get("preferred_candidate") else 1,
            -float(candidate.get("adv30_usd") or 0),
            float(candidate.get("median_spread_pct") or float("inf")),
            -float(candidate.get("aum_usd") or 0),
            -int(candidate.get("valid_history_sessions") or 0),
            int(candidate.get("candidate_priority") or 10**9),
            ticker,
        )

    return sorted(eligible, key=selection_key)[0]["ticker"]


def prepare_registry_themes(snapshot: dict[str, Any], raw: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    """Build price-metric rows for the runtime-selected ETF from every registry record.

    Imported v6.1 snapshots contain only their earlier anchors. Resolve current
    candidate eligibility first, then materialize a row for each eligible
    exposure so the shared v5 score calculation ranks the expanded universe.
    """
    from .collect import _anchor_summary

    settings = snapshot.get("settings", {})
    session = snapshot.get("session_date")
    calendar = raw.get("session_calendar", [])
    charts = raw.get("charts", {})
    old_themes = snapshot.get("themes", [])
    by_id = {row.get("id"): row for row in old_themes}
    rows_by_ticker = {row.get("anchor"): row for row in old_themes}
    spy_chart = charts.get("SPY")
    result = []

    for record in registry.get("themes", []):
        old = by_id.get(record.get("id"))
        if old is None and record.get("anchor"):
            old = rows_by_ticker.get(record.get("anchor"))
        candidates = [
            _candidate_status(record, ticker, raw, snapshot, settings)
            for ticker in record.get("candidate_anchors", [])
        ]
        selected = _select_anchor(record, candidates, old.get("anchor") if old else None)
        if not selected:
            continue

        same_anchor = bool(old and old.get("anchor") == selected)
        review = (record.get("candidate_reviews") or {}).get(selected, {})
        profile = {
            **record,
            "anchor": selected,
            "unleveraged_equity_etf_review": review.get("status") == "reviewed",
            "anchor_instrument_review": review.get("rationale"),
            "anchor_url": review.get("source_url"),
        }
        chart = charts.get(selected)
        anchor_summary = _anchor_summary(
            profile, chart, spy_chart, calendar, session, settings,
            raw.get("errors", {}).get("charts", {}).get(selected),
        )
        theme = dict(old) if same_anchor else {}
        for key in (
            "id", "name", "scope", "included", "excluded", "parent_sector",
            "representation_limit", "level",
        ):
            if key in record:
                theme[key] = record[key]
        theme.update({
            "id": record.get("id"),
            "name": record.get("name"),
            "anchor": selected,
            "level": record.get("level", "Theme"),
            "anchor_url": review.get("source_url"),
            "anchor_instrument_review": review.get("rationale"),
            "anchor_rationale": record.get("anchor_rationale") if selected == record.get("anchor") else "Selected by current candidate mandate, instrument, history, and liquidity checks.",
            "holdings_source": dict(record.get("holdings_source") or {}) if same_anchor else {},
            "selected": list(old.get("selected", [])) if same_anchor else [],
            "reviewed_universe": list(old.get("reviewed_universe", [])) if same_anchor else [],
            "anchor_screen": anchor_summary,
            "returns": anchor_summary["returns"],
            "excess_returns": anchor_summary["excess_returns"],
            "relative_state": anchor_summary["relative_state"],
            "trend": anchor_summary["trend"],
            "trend_status": anchor_summary["trend_status"],
            "trend_reason": anchor_summary["trend_reason"],
            "ema21": anchor_summary["ema21"],
            "ema50": anchor_summary["ema50"],
            "ema21_slope_5": anchor_summary["ema21_slope_5"],
            "session_date": session,
        })
        result.append(theme)

    snapshot["themes"] = result
    return snapshot


def apply_v6(snapshot: dict[str, Any], raw: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    """Audit all configured candidates and publish only runtime-eligible anchors."""
    by_id = {row.get("id"): row for row in snapshot.get("themes", [])}
    rows_by_ticker = {row.get("anchor"): row for row in snapshot.get("themes", [])}
    settings = snapshot.get("settings", {})
    diagnostics = []
    published_ids: set[str] = set()
    for record in registry.get("themes", []):
        theme = by_id.get(record.get("id"))
        if theme is None and record.get("anchor"):
            # Migrate previously generated runs by their unchanged ETF anchor
            # when the registry adopts the v6 stable ID.
            theme = rows_by_ticker.get(record.get("anchor"))
            if theme is not None:
                theme["legacy_registry_id"] = theme.get("id")
                theme["id"] = record.get("id")
        candidates = []
        for ticker in record.get("candidate_anchors", []):
            candidates.append(_candidate_status(record, ticker, raw, snapshot, settings))
        selected = _select_anchor(record, candidates, theme.get("anchor") if theme else None)
        if selected:
            published_ids.add(record["id"])
            status = "selected_anchor"
            selected_reason = (record.get("anchor_rationale") or "Selected by deterministic mandate/source/liquidity/history priority after run-time eligibility checks.")
        else:
            status = "inactive_this_run"
            selected_reason = None
        diagnostics.append({
            "id": record.get("id"),
            "name": record.get("name"),
            "type": record.get("level") if record.get("level") in ("Sector", "Theme") else "Theme",
            "charter_status": record.get("charter_status", "needs_review"),
            "charter": record.get("charter"),
            "status": status,
            "selected_anchor": selected,
            "selected_anchor_reason": selected_reason,
            "candidates": candidates,
            "inactive_reason": None if selected else "; ".join(dict.fromkeys(reason for candidate in candidates for reason in candidate.get("reasons", []))) or "No candidate ETF is configured.",
        })

    # Preserve scored candidate rows internally so excluded/unavailable reasons
    # remain inspectable; dashboard rankings contain only eligible anchors.
    snapshot["candidate_metrics"] = snapshot.get("themes", [])
    snapshot["themes"] = [row for row in snapshot.get("themes", []) if row.get("id") in published_ids]
    _populate_sector_watchlists(snapshot, raw, registry)
    for row in snapshot["themes"]:
        selected_count = len(row.get("selected") or [])
        row["has_curated_watchlist"] = selected_count > 0
        row["curated_watchlist_count"] = selected_count
        row["stock_scope"] = "Curated watchlist" if selected_count else "ETF-only"
        if selected_count:
            row["stock_drilldown_status"] = "available"
        elif row.get("stock_drilldown_status") not in {"retrieval_failed", "no_eligible", "not_configured"}:
            configured = row.get("stock_membership_configured")
            if configured is None:
                configured = bool(row.get("stock_membership_count") or row.get("reviewed_data_count") or row.get("stock_audit") or row.get("level") == "Sector")
                row["stock_membership_configured"] = configured
            row["stock_drilldown_status"] = "no_eligible" if configured else "not_configured"
    _validate_stock_watchlist_metadata(snapshot)
    for row in snapshot["themes"]:
        for stock in row.get("selected", []):
            stock["theme_id"] = row["id"]
        for stock in row.get("reviewed_universe", []):
            stock["theme_id"] = row["id"]
    rank_map = average_ranks({row.get("id", ""): row.get("theme_score") for row in snapshot["themes"]})
    for row in snapshot["themes"]:
        row["global_rank"] = rank_map.get(row.get("id"))
        row["rank_method"] = "ThemeScore descending; equal valid scores receive average rank; unavailable scores unranked and last; stable ID display order"
    snapshot["registry_diagnostics"] = diagnostics
    snapshot["source_status"] = _source_status(raw, snapshot)
    diagnostic_by_id = {row.get("id"): row for row in diagnostics}
    for row in snapshot.get("context", []):
        row["fields"] = _field_snapshot(row, snapshot.get("session_date"))
    for row in snapshot.get("themes", []):
        row["score_method"] = row.get("score_method", "price_relative_strength_v6_1")
        row["score_peer_count_21"] = row.get("score_peer_count_21", row.get("ranking_peer_count21"))
        row["score_peer_count_63"] = row.get("score_peer_count_63", row.get("ranking_peer_count63"))
        row["score_unavailable_reason"] = row.get("score_unavailable_reason") or row.get("field_status", {}).get("theme_score", {}).get("reason")
        row["breadth_status_21"] = row.get("breadth_status_21", row.get("field_status", {}).get("etf_breadth21_pct", {}).get("status", "unavailable"))
        row["breadth_status_50"] = row.get("breadth_status_50", row.get("field_status", {}).get("etf_breadth50_pct", {}).get("status", "unavailable"))
        row["breadth_unavailable_reason_21"] = row.get("breadth_unavailable_reason_21", row.get("field_status", {}).get("etf_breadth21_pct", {}).get("reason"))
        row["breadth_unavailable_reason_50"] = row.get("breadth_unavailable_reason_50", row.get("field_status", {}).get("etf_breadth50_pct", {}).get("reason"))
        audit = diagnostic_by_id.get(row.get("id"), {})
        anchor_candidate = next((candidate for candidate in audit.get("candidates", []) if candidate.get("ticker") == row.get("anchor")), {})
        row["anchor_eligibility_status"] = anchor_candidate.get("status", "eligible")
        row["anchor_eligibility_reasons"] = anchor_candidate.get("reasons", [])
        row["breadth_source_status"] = anchor_candidate.get("breadth_status", "unavailable")
        row["breadth_source_reasons"] = anchor_candidate.get("breadth_reasons", [])
        row["fields"] = _field_snapshot(row, snapshot.get("session_date"))
    snapshot["methodology_version"] = registry.get("methodology_version", registry.get("registry_version"))
    snapshot["theme_registry_version"] = registry.get("registry_version")
    snapshot["resolved_market_session"] = snapshot.get("session_date")
    snapshot.setdefault("collection_started_at", snapshot.get("generated_at"))
    snapshot.setdefault("collection_completed_at", snapshot.get("generated_at"))
    snapshot["schema_version"] = "6.2"
    return snapshot


def _validate_stock_watchlist_metadata(snapshot: dict[str, Any]) -> None:
    """Reject stale ETF-only/watchlist labels before generated output is published."""
    for row in snapshot.get("themes", []):
        count = len(row.get("selected") or [])
        expected_scope = "Curated watchlist" if count else "ETF-only"
        if row.get("curated_watchlist_count") != count:
            raise ValueError(f"{row.get('id')}: curated_watchlist_count does not match selected stocks")
        if row.get("has_curated_watchlist") is not (count > 0):
            raise ValueError(f"{row.get('id')}: has_curated_watchlist does not match selected stocks")
        if row.get("stock_scope") != expected_scope:
            raise ValueError(f"{row.get('id')}: stock_scope does not match selected stocks")
        status = row.get("stock_drilldown_status")
        if count and status != "available":
            raise ValueError(f"{row.get('id')}: populated watchlist must have available stock status")
        if not count and status not in {"not_configured", "retrieval_failed", "no_eligible"}:
            raise ValueError(f"{row.get('id')}: empty watchlist has contradictory status {status!r}")
