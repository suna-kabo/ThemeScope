"""Lean daily collector for the configured-watchlist v7 workflow."""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .metrics import completed_session, session_dates
from .price_cache import PriceCache
from .sources import _TableParser, _request, configure_sources, fetch_holdings, fetch_yahoo_chart, request_json
from .v5 import _nasdaq_effective_date, map_iwm_universe


def _direct_map(source: dict[str, Any]) -> dict[str, Any]:
    companies = []
    for row in source.get("rows", []):
        ticker = str(row.get("ticker") or "").strip().upper().replace(".", "-")
        if not ticker or ticker == "-":
            continue
        companies.append({
            "company_id": str(row.get("company_id") or ticker),
            "company": row.get("company") or ticker,
            "symbols": [ticker],
            "source_tickers": [ticker],
            "sector": row.get("sector"),
            "industry": row.get("industry"),
        })
    return {"companies": companies, "excluded_rows": source.get("excluded_rows", []), "unresolved_mappings": [], "source_row_count": len(source.get("rows", []))}


def _fetch_spy_universe() -> dict[str, Any]:
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    body = _request(url)
    parser = _TableParser()
    parser.feed(body.decode("utf-8", "replace"))
    rows = []
    started = False
    for row in parser.rows:
        if row[:2] == ["Symbol", "Security"]:
            started = True
            continue
        if started:
            if len(row) != 8:
                break
            ticker = row[0].replace(".", "-").strip()
            rows.append({"ticker": ticker, "company": row[1], "sector": row[2], "industry": row[3], "company_id": ticker, "security_type": "EQUITY"})
    if len(rows) < 450:
        raise ValueError("S&P 500 constituent parser returned an incomplete list")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {"as_of": now[:10], "observation_date": now[:10], "effective_date": None, "date_semantics": "observation", "universe_label": "Current observed S&P 500 constituent list", "asof_basis": "Current constituent page observed at retrieval", "url": url, "retrieved_at": now, "rows": rows}


def _fetch_qqq_universe() -> dict[str, Any]:
    url = "https://api.nasdaq.com/api/quote/list-type/nasdaq100"
    data = request_json(url).get("data") or {}
    listing = data.get("data") or {}
    rows = [{"ticker": row.get("symbol"), "company": row.get("companyName"), "company_id": row.get("symbol"), "security_type": "EQUITY"} for row in listing.get("rows", [])]
    if len(rows) < 90 or len(rows) != int(listing.get("totalrecords") or 0):
        raise ValueError("Nasdaq-100 constituent response is incomplete")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    date_text = _nasdaq_effective_date(listing.get("date"))
    return {"as_of": date_text, "observation_date": None, "effective_date": date_text, "date_semantics": "effective", "universe_label": "Nasdaq-100 constituent list", "asof_basis": "Nasdaq response date", "url": url, "retrieved_at": now, "rows": rows}


def _universe_for(cache: PriceCache, name: str, fetcher, refresh_date: str) -> dict[str, Any]:
    cached = cache.read_universe(name)
    if cached and str(cached.get("retrieved_at", ""))[:10] == refresh_date:
        cache.stats["universe_hits"] += 1
        return cached
    cache.stats["universe_requests"] += 1
    try:
        source = fetcher()
        cache.stats["universe_updates"] += 1
        cache.save_universe(name, source)
        return source
    except Exception:
        cache.stats["universe_failures"] += 1
        if cached:
            cache.stats["universe_stale_reuses"] += 1
            return {**cached, "_cache_stale": True}
        raise


def _index_universes(cache: PriceCache, sources_config: dict[str, Any], refresh_date: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    universes: dict[str, Any] = {}
    mapped: dict[str, Any] = {}
    errors: dict[str, str] = {}
    try:
        universes["SPY"] = _universe_for(cache, "spy", _fetch_spy_universe, refresh_date)
        mapped["SPY"] = _direct_map(universes["SPY"])
    except Exception as exc:
        errors["SPY"] = f"{type(exc).__name__}: {exc}"
    try:
        universes["QQQ"] = _universe_for(cache, "qqq", _fetch_qqq_universe, refresh_date)
        mapped["QQQ"] = _direct_map(universes["QQQ"])
    except Exception as exc:
        errors["QQQ"] = f"{type(exc).__name__}: {exc}"
    try:
        source_cfg = sources_config["index_constituents"]["IWM"]
        def get_iwm():
            return fetch_holdings({"anchor": "IWM", "holdings_source": {"method": source_cfg["method"], "url": source_cfg["url"]}})
        universes["IWM"] = _universe_for(cache, "iwm", get_iwm, refresh_date)
        mapped["IWM"] = map_iwm_universe(universes["IWM"], {})
        mapped["IWM"]["price_collection"] = {"proxy": "Current IWM holdings", "source_date": universes["IWM"].get("as_of")}
    except Exception as exc:
        errors["IWM"] = f"{type(exc).__name__}: {exc}"
    return universes, mapped, errors


def build_snapshot_v7(root: Path, requested_asof: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch only active ETF, index, volatility, and configured stock prices."""
    from .sources import _YAHOO_BLOCKED_HOSTS

    started = datetime.now(timezone.utc)
    registry = json.loads((root / "config/themes.json").read_text(encoding="utf-8"))
    source_config = json.loads((root / "config/sources.json").read_text(encoding="utf-8"))
    active = json.loads((root / "config/active_anchors.json").read_text(encoding="utf-8"))
    watchlists = json.loads((root / "config/theme_watchlists.json").read_text(encoding="utf-8"))
    configure_sources(source_config)
    _YAHOO_BLOCKED_HOSTS.clear()
    settings = dict(registry.get("settings", {}))
    cache = PriceCache(root / "cache")
    now_ny = datetime.now(ZoneInfo("America/New_York"))
    today = now_ny.date().isoformat()
    spy_wrapper = cache.read("SPY")
    spy_latest = spy_wrapper.get("latest_completed_session") if spy_wrapper else None
    # A completed same-day SPY bar is a session marker. Otherwise one small SPY
    # probe detects the next session; all other symbols remain cache hits until
    # that session is known.
    after_close = (now_ny.hour > 16 or (now_ny.hour == 16 and now_ny.minute >= 30)) and now_ny.weekday() < 5
    state_path = cache.root / 'sessions' / 'market-session.json'
    try:
        last_probe = json.loads(state_path.read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        last_probe = {}
    already_checked_today = last_probe.get('checked_local_date') == today and (last_probe.get('checked_after_close') or not after_close)
    probe_spy = not already_checked_today and not (spy_latest == today and after_close)
    spy_chart, spy_status, spy_error = cache.get_or_fetch("SPY", None, fetch_yahoo_chart, years=2, force=probe_spy)
    errors: dict[str, Any] = {"charts": {}, "universes": {}}
    if spy_error:
        errors["charts"]["SPY"] = spy_error
    if not spy_chart:
        raise RuntimeError("SPY price history is required to resolve the market session")
    session = requested_asof or completed_session(spy_chart, datetime.now(timezone.utc))
    if not session:
        raise RuntimeError("No completed market session is available from SPY")
    universes, mapped, universe_errors = _index_universes(cache, source_config, today)
    errors["universes"].update(universe_errors)

    symbols = {"SPY", "QQQ", "IWM", *registry.get("volatility_symbols", ["^VIX"]), *active.get("anchors", {}).values()}
    for record in watchlists.get("watchlists", []):
        symbols.update(str(member.get("ticker", "")).upper() for member in record.get("members", []))
    for item in mapped.values():
        symbols.update(symbol for company in item.get("companies", []) for symbol in company.get("symbols", []))
    symbols.discard("")
    charts: dict[str, Any] = {"SPY": spy_chart}
    outcomes: dict[str, str] = {"SPY": spy_status}
    chart_errors: dict[str, str] = {}
    pending = sorted(symbols - {"SPY"})
    session_path = cache.root / 'sessions' / (session + '.json')
    try:
        prior_session_state = json.loads(session_path.read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        prior_session_state = {}
    previous_failures = prior_session_state.get('failed_symbols', {}) if prior_session_state.get('session_date') == session else {}

    def fetch_one(symbol: str):
        if symbol in previous_failures:
            wrapper = cache.read(symbol)
            cache.stats['session_failure_reuses'] += 1
            return symbol, (wrapper.get('chart') if wrapper else None, 'failed_cached', previous_failures[symbol])
        return symbol, cache.get_or_fetch(symbol, session, fetch_yahoo_chart, years=2)
    # Four workers caps concurrency; PriceCache performs validation and atomic
    # merges, while source adapters retain the two-host 429 circuit breaker.
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {pool.submit(fetch_one, symbol): symbol for symbol in pending}
        for future in as_completed(jobs):
            symbol = jobs[future]
            chart, outcome, error = future.result()[1]
            outcomes[symbol] = outcome
            if chart:
                charts[symbol] = chart
            if error:
                chart_errors[symbol] = error
    errors["charts"].update(chart_errors)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_temp = state_path.with_suffix('.tmp')
    state_temp.write_text(json.dumps({'checked_local_date': today, 'checked_after_close': after_close, 'resolved_session': session}, sort_keys=True) + '\n', encoding='utf-8')
    os.replace(state_temp, state_path)
    calendar = [day for day in session_dates(spy_chart) if day <= session]
    if session not in calendar:
        raise RuntimeError(f"SPY chart does not contain requested market session {session}")
    active_registry = dict(registry)
    anchors = active.get("anchors", {})
    inactive = {row.get("theme_id"): row for row in active.get("inactive_records", [])}
    active_registry["themes"] = []
    for record in registry.get("themes", []):
        item = dict(record)
        ticker = anchors.get(record.get("id"))
        item["candidate_anchors"] = [ticker] if ticker else []
        if ticker:
            item["anchor"] = ticker
        elif record.get("id") in inactive:
            item["_v7_preserved_inactive"] = inactive[record.get("id")]
        active_registry["themes"].append(item)
    context = [{"ticker": ticker} for ticker in registry.get("context_symbols", ["SPY", "QQQ", "IWM"])]
    snapshot = {
        "generated_at": started.isoformat(timespec="seconds"),
        "collection_started_at": started.isoformat(timespec="seconds"),
        "collection_completed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session_date": session,
        "run_date": today,
        "requested_asof": requested_asof,
        "timezone": "America/New_York",
        "registry_version": registry.get("registry_version"),
        "settings": settings,
        "score_methodology": registry.get("score_methodology", {}),
        "benchmark": "SPY",
        "session_calendar_source": "SPY",
        "benchmark_status": "valid",
        "context": context,
        "volatility_context": [{"ticker": symbol, "name": "CBOE Volatility Index" if symbol == "^VIX" else symbol, "instrument_type": "volatility_index"} for symbol in registry.get("volatility_symbols", ["^VIX"])],
        "themes": [],
        "comparisons": [],
        "limitations": [
            "Theme breadth uses the configured tradable stock watchlist and does not affect Theme Score or state.",
            "IWM holdings are used as a practical Russell 2000 proxy; this is not an official point-in-time Russell 2000 universe.",
            "Yahoo chart adjusted-close semantics and publication timing are vendor conventions.",
        ],
        "methodology_version": "7.1",
    }
    raw = {
        "charts": {symbol: chart for symbol, chart in charts.items() if symbol in {"SPY", "QQQ", "IWM", "^VIX", *anchors.values()}},
        "session_calendar": calendar,
        "errors": {"charts": chart_errors, "quotes": {}, "holdings": {}, "sec": {}},
        "source_configuration": source_config,
        "v5": {
            "index_universes": universes,
            "mapped_universes": mapped,
            "charts": {symbol: chart for symbol, chart in charts.items() if symbol not in {"SPY", "QQQ", "IWM", "^VIX", *anchors.values()} and symbol not in mapped},
            "chart_errors": chart_errors,
            "iwm_breadth_charts": {symbol: charts[symbol] for symbol in mapped.get("IWM", {}).get("symbols", []) if symbol in charts},
            "iwm_breadth_errors": {},
            "iwm_breadth_diagnostics": {"source_rows": len(universes.get("IWM", {}).get("rows", [])), "downloaded_histories": sum(1 for symbol in charts if symbol in {sym for company in mapped.get("IWM", {}).get("companies", []) for sym in company.get("symbols", [])}), "reused_histories": sum(outcome == "hit" for symbol, outcome in outcomes.items() if symbol in {sym for company in mapped.get("IWM", {}).get("companies", []) for sym in company.get("symbols", [])})},
        },
        "cache": {**cache.stats, "symbols": len(symbols), "outcomes": outcomes, "universe_sources": {key: "cache" if key in universes and str(universes[key].get("retrieved_at", ""))[:10] != today else "updated" for key in universes}, "same_session_spy_reuse": not probe_spy},
    }
    # Keep the IWM mappings available to v5 breadth while carrying the full
    # symbol->chart dictionary separately (the legacy field is a company list).
    iwm_symbols = {symbol for company in mapped.get("IWM", {}).get("companies", []) for symbol in company.get("symbols", [])}
    raw["v5"]["iwm_breadth_charts"] = {symbol: charts[symbol] for symbol in sorted(iwm_symbols) if symbol in charts}
    raw["v5"]["iwm_breadth_errors"] = {symbol: chart_errors[symbol] for symbol in sorted(iwm_symbols) if symbol in chart_errors}
    raw["v5"]["index_errors"] = {key: value for key, value in universe_errors.items()}
    raw["v7_registry"] = active_registry
    raw["watchlists"] = watchlists
    raw["price_cache_stats"] = cache.stats
    raw["price_cache_outcomes"] = outcomes
    cap_path = root / "cache" / "market_cap.json"
    try:
        market_cap_cache = json.loads(cap_path.read_text(encoding="utf-8")).get("symbols", {})
    except (OSError, ValueError, TypeError):
        market_cap_cache = {}
    raw["market_cap_cache"] = market_cap_cache
    raw["collection_request_counts"] = {"price_history": cache.stats["requests"], "universe": cache.stats["universe_requests"], "filings": 0, "quotes": 0, "theme_holdings": 0, "aum_spread": 0}
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_record = {'session_date': session, 'failed_symbols': chart_errors, 'outcomes': outcomes, 'completed_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}
    session_temp = session_path.with_suffix('.tmp')
    session_temp.write_text(json.dumps(session_record, sort_keys=True) + '\n', encoding='utf-8')
    os.replace(session_temp, session_path)
    snapshot["generated_at"] = snapshot["collection_completed_at"]
    return snapshot, raw
