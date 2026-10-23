#!/usr/bin/env python3
"""Collect current public-source inputs and regenerate the static ThemeScope deliverables."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import zipfile
import tempfile
import shutil
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.themescope.collect import build_snapshot  # noqa: E402
from src.themescope.presentation import enrich, validate
from src.themescope.v5 import apply as apply_v5
from src.themescope.v6 import apply_v6
from src.themescope.metrics import return_metric, trend_metric


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _ensure_v61_market_records(snapshot: dict[str, Any], raw: dict[str, Any], registry: dict[str, Any]) -> None:
    """Add explicit unavailable records when importing a pre-v6.1 real run."""
    session = snapshot.get('session_date')
    calendar = raw.get('session_calendar', [])
    context = {row.get('ticker'): row for row in snapshot.setdefault('context', [])}
    for symbol in registry.get('context_symbols', ['SPY', 'QQQ', 'IWM']):
        if symbol in context:
            continue
        chart = raw.get('charts', {}).get(symbol)
        returns = {str(window): return_metric(chart, calendar, session, window) if chart else {'value': None, 'status': 'unavailable', 'reason': 'Price history was not included in this imported run'} for window in (5, 21, 63)}
        trend = trend_metric(chart, calendar, session, snapshot.get('settings', {})) if chart else {'state': 'Unavailable', 'status': 'unavailable', 'reason': 'Price history was not included in this imported run'}
        context[symbol] = {'ticker': symbol, 'returns': returns, 'trend': trend.get('state'), 'trend_status': trend.get('status'), 'trend_reason': trend.get('reason'), 'source_url': chart.get('url') if chart else None}
    snapshot['context'] = [context[symbol] for symbol in registry.get('context_symbols', ['SPY', 'QQQ', 'IWM'])]
    if 'volatility_context' not in snapshot:
        snapshot['volatility_context'] = [{
            'ticker': symbol, 'name': 'CBOE Volatility Index' if symbol == '^VIX' else symbol,
            'instrument_type': 'volatility_index',
            'source_status': 'available' if symbol in raw.get('charts', {}) else 'unavailable',
            'source_reason': raw.get('errors', {}).get('charts', {}).get(symbol) or ('not present in imported run' if symbol not in raw.get('charts', {}) else None),
            'source_url': raw.get('charts', {}).get(symbol, {}).get('url'),
            'retrieved_at': raw.get('charts', {}).get(symbol, {}).get('retrieved_at'),
        } for symbol in registry.get('volatility_symbols', ['^VIX'])]
    context_holdings = raw.get('context_holdings', {})
    if context_holdings:
        from src.themescope.v5 import map_universe
        v5 = raw.setdefault('v5', {})
        universes = v5.setdefault('index_universes', {})
        mapped = v5.setdefault('mapped_universes', {})
        security_mapping = v5.get('security_mapping', {})
        for symbol, source in context_holdings.items():
            universes[symbol] = source
            mapped[symbol] = map_universe(source, security_mapping, index=True)


def _source_row(
    field: str,
    scope: str,
    provider: str,
    method: str,
    history_or_as_of: str,
    delay_and_availability: str,
    limitations: str,
    fallback: str,
    last_test: str,
    retrieved_at: str | None,
    url: str | None,
) -> dict[str, str | None]:
    return {
        "field": field,
        "scope": scope,
        "provider": provider,
        "method": method,
        "history_or_as_of": history_or_as_of,
        "delay_and_availability": delay_and_availability,
        "limitations": limitations,
        "fallback": fallback,
        "last_test": last_test,
        "retrieved_at": retrieved_at,
        "url": url,
    }


def make_source_matrix(snapshot: dict[str, Any], raw: dict[str, Any], root: Path) -> list[dict[str, str | None]]:
    rows = []
    def add(field, scope, provider, method, source, limitations):
        observations = source.get('observations') or []
        effective = source.get('as_of') or source.get('effective_date') or source.get('session_date') or (observations[-1].get('date') if observations else None)
        rows.append(dict(field=field, scope=scope, provider=provider, method=method, as_of=effective, retrieved_at=source.get('retrieved_at'), url=source.get('url'), payload_kind=None, payload_sha256=None, limitations=limitations))
    source_config = raw.get('source_configuration', {})
    price_config = source_config.get('prices', {})
    rows.append(dict(
        field='Source priority and fallback configuration', scope='All retrieved price histories',
        provider=price_config.get('provider', 'Yahoo Finance chart API'),
        method=' → '.join(price_config.get('hosts', [])), as_of=None, retrieved_at=None, url=None,
        payload_kind=None, payload_sha256=None,
        limitations=price_config.get('fallback_policy', 'Source configuration unavailable.'),
    ))
    add('Adjusted returns and split-adjusted closes/EMA; split events for ADV', 'SPY, QQQ, ETF anchors and accepted stocks', 'Yahoo Finance', 'Daily chart endpoint; sequential 1.5s default pacing, query2 fallback; stop host after HTTP 429', raw.get('charts', {}).get('SPY', {}), 'Undocumented provider convention. Only completed common US sessions. No silent adjustment substitution.')
    add('Breadth price histories', 'Mapped index and anchor constituents', 'Yahoo Finance', 'Same chart schema and EMA warmups as core; count companies once', next(iter(raw.get('v5', {}).get('charts', {}).values()), {}), 'Unmapped foreign listings remain missing in coverage; no guessed listing substitutions.')
    for symbol, source in raw.get('v5', {}).get('index_universes', {}).items():
        if symbol == 'IWM':
            # IWM is sourced from official iShares holdings and is deliberately
            # reported separately below as a practical Russell 2000 proxy.
            continue
        provider = 'Nasdaq' if symbol == 'QQQ' else 'Wikipedia current S&P 500 constituent table'
        add('Index constituent universe', symbol, provider, 'Reproducible constituent list; source rows retained', source, source.get('asof_basis', ''))
    add('Verified issuer/listing map', 'Company deduplication and ticker mapping', 'SEC', 'company_tickers_exchange.json; deterministic primary share class', raw.get('v5', {}).get('security_mapping', {}), 'SEC CIK identifies issuers. Unverified mappings are not invented; common company IDs are deduplicated.')
    for symbol, source in raw.get('holdings', {}).items():
        add('Official equity holdings', symbol, 'Fund issuer', 'Official JSON/HTML/CSV/XLSX adapter; actual as-of date retained', source, 'Breadth is equal-company participation, independent of watchlist curation. Excluded and unmapped rows recorded.')
    for symbol, source in raw.get('context_holdings', {}).items():
        add('Official equity holdings', symbol, 'iShares', 'Official ETF holdings CSV; practical Russell 2000 proxy', source, 'IWM holdings breadth is not official Russell 2000 constituent breadth; holdings as-of is separate from price session.')
    for item in snapshot.get('volatility_context', []):
        add('Volatility level and changes', item.get('ticker'), 'Yahoo Finance', 'Daily chart close observations; no breadth or score dependency', raw.get('charts', {}).get(item.get('ticker'), {}), 'VIX is independent volatility context.')
    add('Market capitalization and stock eligibility', 'Accepted watchlist candidates', 'Nasdaq', 'Quote summary endpoint', next(iter(raw.get('quotes', {}).values()), {}), 'No separate market-cap field timestamp; stock eligibility remains provisional.')
    for theme in snapshot.get('themes', []):
        for member in theme.get('reviewed_universe', theme.get('selected', [])):
            source = {'url': member.get('membership_source') or member.get('evidence', {}).get('url'), 'as_of': member.get('reviewed_date')}
            add('Membership rationale', theme['id']+':'+member['ticker'], 'Recorded issuer/evidence source', member.get('membership_tag') or member.get('evidence_category'), source, member.get('membership_rationale') or member.get('evidence_note', ''))
    for item in raw.get('cache_manifest', []):
        rows.append(dict(
            field='Normalized source payload hash', scope=f"{item.get('dataset')}:{item.get('key')}",
            provider=item.get('source'), method='SHA-256', as_of=item.get('effective_asof'),
            retrieved_at=item.get('retrieved_at'), url=item.get('url'),
            payload_kind=item.get('payload_kind'), payload_sha256=item.get('sha256'),
            limitations='Hash is over the normalized retained source payload, not original HTTP wire bytes.',
        ))
    return rows


EXPORT_COLUMNS = [
    "membership_tag", "membership_source", "membership_rationale", "is_anchor_holding", "price_close", "return5", "excess5_pp", "above_ema21", "above_ema50",
    "theme", "theme_id", "anchor", "selection_slot", "selection_queue", "selection_queue_rank",
    "selection_reason", "ticker", "company", "exchange", "security_type", "evidence_category",
    "evidence_note", "evidence_url", "evidence_filed_date", "reviewed_date", "etf_weight_pct",
    "market_cap_usd", "market_cap_retrieved_at", "adv30_usd", "return21", "return63",
    "excess21_pp", "excess63_pp", "relative_state", "price_trend", "session_date", "generated_at", "chart_url",
]


def _number(metric: dict[str, Any] | None) -> float | None:
    if not metric or metric.get("status") != "valid":
        return None
    return metric.get("value")


def _all_selected(snapshot: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    rows = []
    for theme in snapshot.get("themes", []):
        for stock in sorted(theme.get("selected", []), key=lambda row: row.get("selection_slot", 10**9))[:limit]:
            exchange = str(stock.get("exchange") or "").upper()
            prefix = "NASDAQ" if exchange.startswith("NASDAQ") else ("NYSE" if exchange.startswith("NYSE") else "")
            chart_url = f"https://www.tradingview.com/chart/?symbol={prefix}:{stock['ticker']}" if prefix else None
            evidence = stock.get("evidence") or {}
            rows.append({
                **{key: stock.get(key) for key in ('membership_tag','membership_source','membership_rationale','is_anchor_holding','price_close')},
                'return5': _number(stock.get('returns', {}).get('5')),
                'excess5_pp': (value*100 if (value := _number(stock.get('excess_returns', {}).get('5'))) is not None else None),
                'above_ema21': stock.get('price_close') > stock['ema21'] if stock.get('price_close') is not None and stock.get('ema21') is not None else None,
                'above_ema50': stock.get('price_close') > stock['ema50'] if stock.get('price_close') is not None and stock.get('ema50') is not None else None,
                "theme": theme["name"], "theme_id": theme["id"], "anchor": theme["anchor"],
                "selection_slot": stock.get("selection_slot"), "selection_queue": stock.get("selection_queue"),
                "selection_queue_rank": stock.get("selection_queue_rank"), "selection_reason": stock.get("selection_reason"),
                "ticker": stock.get("ticker"), "company": stock.get("company"), "exchange": stock.get("exchange"),
                "security_type": stock.get("security_type"), "evidence_category": stock.get("evidence_category"),
                "evidence_note": stock.get("evidence_note"), "evidence_url": evidence.get("url"),
                "evidence_filed_date": evidence.get("filed_date"), "reviewed_date": stock.get("reviewed_date"),
                "etf_weight_pct": stock.get("etf_weight_pct"), "market_cap_usd": stock.get("market_cap_usd"),
                "market_cap_retrieved_at": stock.get("market_cap_retrieved_at"), "adv30_usd": stock.get("adv30_usd"),
                "return21": _number(stock.get("returns", {}).get("21")),
                "return63": _number(stock.get("returns", {}).get("63")),
                "excess21_pp": (value * 100 if (value := _number(stock.get("excess_returns", {}).get("21"))) is not None else None),
                "excess63_pp": (value * 100 if (value := _number(stock.get("excess_returns", {}).get("63"))) is not None else None),
                "relative_state": stock.get("relative_state"), "price_trend": stock.get("trend"),
                "session_date": stock.get("session_date"), "generated_at": snapshot.get('dashboard_generated_at') or snapshot.get('generated_at'), "chart_url": chart_url,
            })
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _tradingview_text(rows: list[dict[str, Any]]) -> tuple[str, dict[str, int]]:
    seen: set[str] = set()
    symbols: list[str] = []
    omitted = 0
    duplicates = 0
    for row in rows:
        ticker = str(row.get("ticker") or "")
        exchange = str(row.get("exchange") or "").upper()
        prefix = "NASDAQ" if exchange.startswith("NASDAQ") else ("NYSE" if exchange.startswith("NYSE") else "")
        if not prefix:
            omitted += 1
            continue
        symbol = f"{prefix}:{ticker}"
        if symbol in seen:
            duplicates += 1
            continue
        seen.add(symbol)
        symbols.append(symbol)
    return ("\n".join(symbols) + ("\n" if symbols else ""), {"unique": len(symbols), "omitted": omitted, "duplicates": duplicates})


def _stock_diagnostics(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for exposure in snapshot.get('themes', []):
        rows = exposure.get('stock_audit')
        if rows is None:
            rows = list(exposure.get('reviewed_universe', []))
        for row in rows:
            output.append({
                'theme_id': exposure.get('id'), 'theme': exposure.get('name'), 'type': exposure.get('level'),
                'anchor': exposure.get('anchor'), 'ticker': row.get('ticker'), 'company': row.get('company'),
                'eligibility': row.get('eligibility'), 'eligibility_reasons': '; '.join(row.get('eligibility_reasons', [])),
                'membership_tag': row.get('membership_tag'), 'membership_source': row.get('membership_source'),
                'membership_rationale': row.get('membership_rationale'), 'security_type': row.get('security_type'),
                'exchange': row.get('exchange'), 'market_cap_usd': row.get('market_cap_usd'),
                'market_cap_status': row.get('market_cap_status'), 'market_cap_retrieved_at': row.get('market_cap_retrieved_at'),
                'raw_close': row.get('raw_close'), 'adv30_usd': row.get('adv30_usd'),
                'return5': _number(row.get('returns', {}).get('5')), 'return21': _number(row.get('returns', {}).get('21')),
                'return63': _number(row.get('returns', {}).get('63')),
                'excess21_pp': (100 * value if (value := _number(row.get('excess_returns', {}).get('21'))) is not None else None),
                'excess63_pp': (100 * value if (value := _number(row.get('excess_returns', {}).get('63'))) is not None else None),
                'selection_slot': row.get('selection_slot'), 'selection_queue': row.get('selection_queue'),
                'selection_queue_rank': row.get('selection_queue_rank'), 'selection_reason': row.get('selection_reason'),
                'chart_source': row.get('chart_source'), 'quote_source': row.get('quote_source'),
                'session_date': row.get('session_date') or snapshot.get('session_date'),
            })
        if exposure.get('stock_audit') is None:
            for row in exposure.get('exclusions', []):
                output.append({
                    'theme_id': exposure.get('id'), 'theme': exposure.get('name'), 'type': exposure.get('level'),
                    'anchor': exposure.get('anchor'), 'ticker': row.get('ticker'), 'company': row.get('company'),
                    'eligibility': 'excluded_or_unavailable',
                    'eligibility_reasons': '; '.join(row.get('reasons', row.get('eligibility_reasons', []))),
                    'membership_tag': row.get('membership_tag'),
                    'membership_source': row.get('membership_source') or row.get('source_url') or (row.get('evidence') or {}).get('url'),
                    'membership_rationale': row.get('membership_rationale') or row.get('evidence_note'),
                    'market_cap_usd': row.get('market_cap_usd'), 'adv30_usd': row.get('adv30_usd'),
                    'session_date': snapshot.get('session_date'),
                })
            for row in exposure.get('pending_holdings', []):
                output.append({
                    'theme_id': exposure.get('id'), 'theme': exposure.get('name'), 'type': exposure.get('level'),
                    'anchor': exposure.get('anchor'), 'ticker': row.get('ticker'), 'company': row.get('company'),
                    'eligibility': row.get('status', 'pending_review'), 'eligibility_reasons': row.get('reason'),
                    'membership_source': (row.get('evidence') or {}).get('url'),
                    'session_date': snapshot.get('session_date'),
                })
        if exposure.get('level') == 'Sector':
            for row in exposure.get('sector_member_exclusions', []):
                output.append({
                    'theme_id': exposure.get('id'), 'theme': exposure.get('name'), 'type': 'Sector',
                    'anchor': exposure.get('anchor'), 'ticker': row.get('ticker'), 'company': row.get('company'),
                    'eligibility': 'excluded_or_unmapped', 'eligibility_reasons': row.get('reason'),
                    'membership_source': exposure.get('sector_membership_basis', {}).get('method'),
                    'session_date': snapshot.get('session_date'),
                })
    return output


def _run_report(snapshot: dict[str, Any], raw: dict[str, Any], matrix: list[dict[str, Any]], tv15: dict[str, int], tv20: dict[str, int]) -> str:
    lines = ['# ThemeScope v6.1 run report', '', f"Market session: {snapshot['session_date']}", f"Dashboard generated: {snapshot.get('dashboard_generated_at')} ({snapshot.get('dashboard_generated_at_hkt_display')})", f"Latest source retrieval: {snapshot.get('last_source_retrieved_at') or snapshot.get('collection_completed_at')}", f"Base collection: {snapshot.get('collection_started_at')} to {snapshot.get('collection_completed_at')}", f"Requested as-of: {snapshot.get('requested_asof') or 'latest verified completed common session'}", '', '## Market/index facts']
    restored = score_failures = breadth_failures = drilldown_unavailable = 0
    for row in snapshot['context']:
        description = {'SPY': 'S&P 500 ETF', 'QQQ': 'Nasdaq-100 ETF', 'IWM': 'Russell 2000 ETF proxy'}.get(row['ticker'], row['ticker'])
        lines.append(f"- {row['ticker']} ({description}): close {row.get('price_close')}; session {row.get('price_session_date') or row.get('session_date') or snapshot.get('session_date')}; price status {row.get('price_status', 'available' if row.get('price_close') is not None else 'unavailable')}; {row.get('price_reason') or 'valid'}.")
        for window in ('5', '21', '63'):
            metric = row.get('returns', {}).get(window, {})
            lines.append(f"  - Return{window}: {metric.get('value')}; {metric.get('status')}; {metric.get('reason') or 'valid'}.")
        for period in (21,50):
            m = row.get('index_breadth', {}).get(str(period), {})
            relation = 'above' if row.get(f'above_ema{period}') is True else 'at/below' if row.get(f'above_ema{period}') is False else 'unavailable'
            breadth_label = 'IWM holdings breadth' if row['ticker'] == 'IWM' else 'constituent breadth'
            lines.append(f"  - Close {relation} EMA{period} ({row.get('ema' + str(period))}); {breadth_label} {m.get('above_count')}/{m.get('valid_count')} valid, {m.get('eligible_count')} eligible, {m.get('coverage_pct')}% coverage, holdings/list as of {m.get('as_of')}; {m.get('status', 'unavailable')}: {m.get('reason') or 'valid'}")
    lines += ['', '## Volatility context']
    for item in snapshot.get('volatility_context', []):
        lines.append(f"- {item.get('ticker')}: level {item.get('level')}; daily {item.get('daily_change')}; 5-session {item.get('return5')}; 21-session {item.get('return21')}; trailing 1-year percentile {item.get('trailing_1y_percentile')}; observation date {item.get('observation_date')}; retrieved {item.get('retrieved_at')}; {item.get('source_status')}: {item.get('source_reason') or item.get('source_url') or 'valid'}. No breadth fields or score dependency.")
    weights = snapshot.get('score_methodology', {}).get('theme_score_weights', {})
    current_weight = weights.get('current_strength', 0.6)
    medium_weight = weights.get('medium_strength', 0.4)
    minimum_peers = snapshot.get('score_methodology', {}).get('minimum_peers', 10)
    lines += ['', '## Eligible primary ETF ranking', f"Current is the 21-session excess-return percentile; Medium is the 63-session excess-return percentile; Theme Score = {current_weight:.0%} Current + {medium_weight:.0%} Medium. Percentiles require at least {minimum_peers} valid peers. Breadth and curated stocks do not enter score or state."]
    for row in snapshot['themes']:
        candidate = next((c for d in snapshot.get('registry_diagnostics', []) if d.get('id') == row.get('id') for c in d.get('candidates', []) if c.get('ticker') == row.get('anchor')), {})
        restored += int(candidate.get('status') == 'eligible' and not candidate.get('holdings_source_configured'))
        score_failures += int(row.get('theme_score') is None)
        breadth_failures += int(row.get('breadth_status_21') != 'valid' or row.get('breadth_status_50') != 'valid')
        drilldown_unavailable += int(not row.get('has_curated_watchlist', bool(row.get('selected'))))
        drilldown = 'available (' + str(len(row.get('selected', []))) + ')' if row.get('selected') else 'unavailable'
        lines.append(f"- {row['name']} ({row['anchor']}), {row.get('level')}: score {row.get('theme_score')}; state {row.get('theme_state')}; curated stock drilldown {drilldown}; anchor eligibility {candidate.get('status', 'eligible')}.")
        for field in ('percentile_excess21','percentile_excess63','etf_breadth21_pct','etf_breadth50_pct','current_strength_score','medium_strength_score','theme_score'):
            item = row.get('field_status', {}).get(field, {})
            lines.append(f"  - {field}: {row.get(field)}; {item.get('status')}; {item.get('reason') or 'valid'}")
        lines.append(f"  - Score peers: 21-session {row.get('score_peer_count_21')}; 63-session {row.get('score_peer_count_63')}; method {row.get('score_method')}; unavailable reason {row.get('score_unavailable_reason') or 'none'}.")
        lines.append(f"  - Breadth: EMA21 {row.get('breadth_status_21')}: {row.get('breadth_unavailable_reason_21') or 'valid'}; EMA50 {row.get('breadth_status_50')}: {row.get('breadth_unavailable_reason_50') or 'valid'}.")
        universe = raw.get('v5', {}).get('mapped_universes', {}).get(row['anchor'], {})
        lines.append(f"  - {len(universe.get('excluded_rows', []))} excluded source rows; {len(universe.get('unresolved_mappings', []))} unresolved equity mappings remain in coverage denominator.")
    icln = next((row for row in snapshot.get('themes', []) if row.get('anchor') == 'ICLN'), None)
    if icln:
        universe = raw.get('v5', {}).get('mapped_universes', {}).get('ICLN', {})
        lines += ['', '## ICLN score and breadth diagnostic', f"- Current {icln.get('current_strength_score')}; Medium {icln.get('medium_strength_score')}; Theme Score {icln.get('theme_score')}; state {icln.get('theme_state')}.", f"- EMA21 breadth: {icln.get('breadth_status_21')}; {icln.get('breadth_unavailable_reason_21') or 'valid'}.", f"- EMA50 breadth: {icln.get('breadth_status_50')}; {icln.get('breadth_unavailable_reason_50') or 'valid'}.", f"- Mapped holdings: {len(universe.get('companies', []))}; unresolved equity mappings: {len(universe.get('unresolved_mappings', []))}; official source rows: {universe.get('source_row_count')}."]
    lines += ['', '## Layer totals', f"- Eligible ETF anchors with no configured holdings parser (restored by removing holdings-parser eligibility gate): {restored}.", f"- ETF score failures: {score_failures}; only ETF/SPY return data and peer availability affect these.", f"- ETF breadth failures: {breadth_failures}; they do not affect ETF eligibility or score.", f"- Curated stock drilldown unavailable: {drilldown_unavailable}; it does not affect ETF eligibility or score."]
    diagnostics = snapshot.get('registry_diagnostics', [])
    active = sum(row.get('status') == 'selected_anchor' for row in diagnostics)
    lines += ['', '## Registry audit', f"- Registry records: {len(diagnostics)}; runtime eligible anchors: {active}; inactive or unresolved this run: {len(diagnostics)-active}."]
    for row in diagnostics:
        lines.append(f"- {row.get('name')} ({row.get('id')}): {row.get('status')}; selected {row.get('selected_anchor') or 'none'}.")
        for candidate in row.get('candidates', []):
            reasons = '; '.join(candidate.get('reasons', [])) or 'passed configured runtime checks'
            lines.append(f"  - {candidate.get('ticker')}: {candidate.get('status')}; {reasons}")
            breadth_reasons = '; '.join(candidate.get('breadth_reasons', []))
            if breadth_reasons:
                lines.append(f"    - Breadth only: {breadth_reasons}")
    settings = snapshot.get('settings', {})
    scores = snapshot.get('score_methodology', {})
    lines += ['', '## Methodology and limits',
        f"- ETF candidates require at least {settings.get('anchor_minimum_history_sessions')} valid price sessions and ${settings.get('anchor_adv30_floor_usd', 0):,.0f} 30-session average dollar volume; AUM/spread are reported unavailable when a reproducible source is not configured.",
        f"- Holdings breadth requires a dated official equity holdings source, at least {settings.get('minimum_breadth_sample')} valid companies, {settings.get('minimum_breadth_coverage', 0)*100:g}% price coverage, and holdings no older than {settings.get('maximum_holdings_age_days')} days. These checks do not enter scoring.",
        f"- Score weights are configured as {json.dumps(scores, sort_keys=True)}. This is a consistent relative-strength ranking for manual review, not a prediction or entry signal.",
        '- Missing score inputs are not imputed or reweighted. ETF and index breadth use complete sourced equity universes independently of curated stock watchlists.',
        '- Index and ETF memberships are current source snapshots, not historical point-in-time universes. Yahoo adjusted-close semantics are vendor conventions.',
        '- Nasdaq market-cap fields have no separate observation timestamps, so stock eligibility remains provisional. Sector stock watchlists use current S&P 500 classifications intersected with official sector ETF holdings and the configured price, cap and liquidity filters.',
        '- Ineligible anchors, unavailable ETF scores, unavailable breadth, and missing curated stock drilldowns are separate statuses. Missing breadth or stocks does not make an ETF ineligible.',
        '', '## Source errors', '```json', json.dumps({'core': raw.get('errors', {}), 'constituent_histories':raw.get('v5', {}).get('chart_errors', {})}, indent=2), '```',
        '', '## Sector stock-list scope', 'Sector stock candidates are the current S&P 500 sector classification intersected with official selected-sector ETF holdings, then filtered by the configured listed-equity, price, market-cap and ADV rules. This is not every listed company in each sector. Per-company evidence and exclusions are in stock_diagnostics.csv.',
        '', '## Local files', 'dashboard.html, market.csv (SPY, QQQ, IWM, VIX with instrument-specific fields), themes.csv, registry_audit.csv, stock_diagnostics.csv, latest_snapshot.json, raw_inputs.json, source_matrix.csv, watchlist_15.csv, watchlist_20.csv, tradingview_15.txt, tradingview_20.txt, run_bundle.zip.', 'Opening HTML never retrieves data. Explicitly run python scripts/generate_dashboard.py. Failed refreshes preserve existing valid exports and write refresh_status.json/failed_refresh.md separately.']
    return '\n'.join(lines)+'\n'


RUN_OUTPUT_FILES = (
    "market.csv", "themes.csv", "registry_audit.csv", "stock_diagnostics.csv",
    "dashboard.html",
    "latest_snapshot.json",
    "raw_inputs.json",
    "source_matrix.csv",
    "watchlist_15.csv",
    "watchlist_20.csv",
    "tradingview_15.txt",
    "tradingview_20.txt",
    "latest_run.md",
)


def _write_run_bundle(output_dir: Path) -> Path:
    bundle_path = output_dir / "run_bundle.zip"
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for filename in RUN_OUTPUT_FILES:
            source = output_dir / filename
            if not source.is_file():
                raise FileNotFoundError(f"Missing run output required for bundle: {source}")
            bundle.write(source, arcname=filename)
    return bundle_path


def _generate(snapshot, raw, output_dir):
    matrix = make_source_matrix(snapshot, raw, ROOT)
    snapshot["source_matrix"] = matrix
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "latest_snapshot.json", snapshot)
    _write_json(output_dir / "raw_inputs.json", raw)
    _write_csv(output_dir / "source_matrix.csv", matrix, list(matrix[0].keys()) if matrix else [])

    theme_records = sorted(snapshot.get('themes', []), key=lambda row: row.get('global_rank', 10**9))
    market_records = list(snapshot.get('context', [])) + list(snapshot.get('volatility_context', []))
    for filename, records in [('market.csv', market_records), ('themes.csv', theme_records)]:
        flat = []
        for record in records:
            row = {k:v for k,v in record.items() if v is None or isinstance(v, (str,int,float,bool))}
            if filename == 'themes.csv':
                row['global_rank'] = record.get('global_rank')
                row['type'] = 'Sector' if record.get('level') == 'Sector' else 'Theme'
            row['session_date'] = snapshot['session_date']
            row['generated_at'] = snapshot.get('dashboard_generated_at') or snapshot['generated_at']
            if record.get('instrument_type') == 'volatility_index':
                row['instrument_type'] = 'volatility_index'
                row.pop('index_breadth', None)
                row.pop('holdings_breadth', None)
            for key, item in record.get('field_status', {}).items():
                for part in ('status','reason','observation_count','session_date','input_version','above_count','valid_count','eligible_count','coverage_pct','peer_count'):
                    row[key+'_'+part] = item.get(part)
            if record.get('instrument_type') != 'volatility_index':
                for window in ('5','21','63'):
                    row['return'+window] = _number(record.get('returns', {}).get(window))
                    value = _number(record.get('excess_returns', {}).get(window))
                    row['excess'+window+'_pp'] = value*100 if value is not None else None
            flat.append(row)
        columns = list(dict.fromkeys(k for row in flat for k in row))
        _write_csv(output_dir / filename, flat, columns)
    registry_rows = []
    for exposure in snapshot.get('registry_diagnostics', []):
        for candidate in exposure.get('candidates', []):
            registry_rows.append({
                'id': exposure.get('id'), 'name': exposure.get('name'), 'type': exposure.get('type'),
                'charter_status': exposure.get('charter_status'), 'charter': exposure.get('charter'),
                'status': exposure.get('status'), 'selected_anchor': exposure.get('selected_anchor'),
                'selected_anchor_reason': exposure.get('selected_anchor_reason'), 'candidate_ticker': candidate.get('ticker'),
                'candidate_priority': candidate.get('candidate_priority'), 'candidate_status': candidate.get('status'),
                'candidate_reasons': '; '.join(candidate.get('reasons', [])), 'fund_name': candidate.get('fund_name'),
                'exchange': candidate.get('exchange'), 'listing_status': candidate.get('listing_status'),
                'instrument_type': candidate.get('instrument_type'), 'currency': candidate.get('currency'),
                'history_status': candidate.get('history_status'), 'valid_history_sessions': candidate.get('valid_history_sessions'),
                'breadth_status': candidate.get('breadth_status'), 'breadth_reasons': '; '.join(candidate.get('breadth_reasons', [])),
                'price_effective_date': candidate.get('price_effective_date'), 'price_retrieved_at': candidate.get('price_retrieved_at'),
                'price_source_url': candidate.get('price_source_url'),
                'adv30_usd': candidate.get('adv30_usd'), 'minimum_adv30_usd': candidate.get('minimum_adv30_usd'),
                'holdings_effective_date': candidate.get('holdings_effective_date'), 'holdings_retrieved_at': candidate.get('holdings_retrieved_at'),
                'source_holdings_rows': candidate.get('source_holdings_rows'), 'mapped_equity_holdings': candidate.get('mapped_equity_holdings'),
                'unresolved_equity_mappings': candidate.get('unresolved_equity_mappings'), 'aum_usd': candidate.get('aum_usd'),
                'aum_status': candidate.get('aum_status'), 'median_spread_pct': candidate.get('median_spread_pct'),
                'spread_status': candidate.get('spread_status'), 'inactive_reason': exposure.get('inactive_reason'),
            })
    _write_csv(output_dir / 'registry_audit.csv', registry_rows, list(registry_rows[0]) if registry_rows else ['id','name','type','status'])
    stock_rows = _stock_diagnostics(snapshot)
    stock_columns = list(stock_rows[0]) if stock_rows else ['theme_id','theme','type','anchor','ticker','company','eligibility','eligibility_reasons','session_date']
    _write_csv(output_dir / 'stock_diagnostics.csv', stock_rows, stock_columns)
    rows15 = _all_selected(snapshot, 15)
    rows20 = _all_selected(snapshot, 20)
    _write_csv(output_dir / "watchlist_15.csv", rows15, EXPORT_COLUMNS)
    _write_csv(output_dir / "watchlist_20.csv", rows20, EXPORT_COLUMNS)
    text15, stats15 = _tradingview_text(rows15)
    text20, stats20 = _tradingview_text(rows20)
    (output_dir / "tradingview_15.txt").write_text(text15, encoding="utf-8")
    (output_dir / "tradingview_20.txt").write_text(text20, encoding="utf-8")
    report = _run_report(snapshot, raw, matrix, stats15, stats20)
    (output_dir / "latest_run.md").write_text(report, encoding="utf-8")

    template = (ROOT / "static/dashboard_template.html").read_text(encoding="utf-8")
    style = (ROOT / "static/dashboard.css").read_text(encoding="utf-8")
    script = (ROOT / "static/dashboard.js").read_text(encoding="utf-8")
    payload = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    html = template.replace("{{STYLE}}", style).replace("{{SCRIPT}}", script).replace("{{SNAPSHOT_JSON}}", payload)
    if "{{STYLE}}" in html or "{{SCRIPT}}" in html or "{{SNAPSHOT_JSON}}" in html:
        raise RuntimeError("Dashboard template placeholder replacement failed")
    (output_dir / "dashboard.html").write_text(html, encoding="utf-8")
    bundle_path = _write_run_bundle(output_dir)

    return bundle_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Explicitly refresh the offline ThemeScope dashboard.")
    parser.add_argument('--output-dir', default='output')
    parser.add_argument('--import-run', type=Path, help='Import a dated real run directory or run_bundle.zip; no network requests')
    parser.add_argument('--as-of', help='Resolve the latest verified completed common US session on or before YYYY-MM-DD')
    args = parser.parse_args(argv)
    if args.as_of:
        try:
            datetime.strptime(args.as_of, '%Y-%m-%d')
        except ValueError:
            parser.error('--as-of must use YYYY-MM-DD')
    output = Path(args.output_dir).expanduser()
    if not output.is_absolute():
        output = ROOT / output
    output = output.resolve()
    if output == ROOT or ROOT.is_relative_to(output):
        parser.error('Output must be a dedicated directory, not the project or its parent')
    output.parent.mkdir(parents=True, exist_ok=True)
    snapshot, raw = {}, {}
    attempted = datetime.now(timezone.utc).isoformat(timespec='seconds')
    try:
        if args.import_run:
            print('Importing dated real data; no collection will run.', flush=True)
            if args.import_run.is_file():
                with zipfile.ZipFile(args.import_run) as bundle:
                    for name in ('latest_snapshot.json','raw_inputs.json'):
                        if bundle.getinfo(name).file_size > 250_000_000:
                            raise ValueError('Imported JSON exceeds 250 MB limit')
                    snapshot = json.loads(bundle.read('latest_snapshot.json').decode('utf-8'))
                    raw = json.loads(bundle.read('raw_inputs.json').decode('utf-8'))
            else:
                snapshot = json.loads((args.import_run / 'latest_snapshot.json').read_text(encoding='utf-8'))
                raw = json.loads((args.import_run / 'raw_inputs.json').read_text(encoding='utf-8'))
            if not snapshot.get('generated_at') or not snapshot.get('session_date'):
                raise ValueError('Imported run must retain its original generation time and session date')
            if args.as_of and args.as_of != snapshot.get('session_date'):
                raise ValueError('This imported bundle contains one resolved date only; use a fresh collection to resolve --as-of.')
            snapshot['imported_at'] = attempted
        else:
            print('Collecting official holdings, paced prices, quotes and filing checks. Please wait.', flush=True)
            snapshot, raw = build_snapshot(ROOT, args.as_of)
        if args.as_of:
            snapshot['requested_asof'] = args.as_of
        registry = json.loads((ROOT / 'config/themes.json').read_text(encoding='utf-8'))
        _ensure_v61_market_records(snapshot, raw, registry)
        snapshot['score_methodology'] = registry.get('score_methodology', {})
        snapshot['methodology_version'] = registry.get('methodology_version', registry.get('registry_version'))
        for theme in snapshot.get('themes', []):
            configured = next((t for t in registry['themes'] if t['id'] == theme['id'] and t['anchor'] == theme['anchor']), {})
            theme.setdefault('level', configured.get('level', 'Theme'))
        enrich(snapshot, raw)
        if snapshot.get("context") and snapshot.get("session_date") and all(
            symbol in raw.get("charts", {}) for symbol in ("SPY", "QQQ")
        ):
            apply_v5(snapshot, raw)
        apply_v6(snapshot, raw, registry)
        from src.themescope.cache import manifest_for_inputs
        raw['cache_manifest'] = manifest_for_inputs(raw, snapshot.get('collection_completed_at') or attempted)
        generated_dt = datetime.now(timezone.utc)
        generated_hkt = generated_dt.astimezone(ZoneInfo('Asia/Hong_Kong'))
        snapshot['dashboard_generated_at'] = generated_dt.isoformat(timespec='seconds')
        snapshot['dashboard_generated_at_hkt'] = generated_hkt.isoformat(timespec='seconds')
        snapshot['dashboard_generated_at_hkt_display'] = generated_hkt.strftime('%d %b %Y, %I:%M %p HKT').lstrip('0')
        snapshot['dashboard_display_timezone'] = 'Asia/Hong_Kong'
        validate(snapshot, raw)
        with tempfile.TemporaryDirectory(prefix='.themescope-stage-', dir=output.parent) as tmp:
            stage = Path(tmp) / 'run'
            stage.mkdir()
            _generate(snapshot, raw, stage)
            _write_json(stage / 'refresh_status.json', {'status': 'success', 'attempted_at': attempted, 'data_date': snapshot['session_date'], 'imported': bool(args.import_run)})
            # Commit only generated files; preserve unrelated files in a custom output directory.
            # Dashboard is published last, after every dependent download is ready.
            output.mkdir(parents=True, exist_ok=True)
            backup = Path(tmp) / 'previous'
            backup.mkdir()
            changed = []
            files = sorted(stage.iterdir(), key=lambda p: p.name == 'dashboard.html')
            retired_files = ('sectors.csv', 'industries.csv')
            try:
                for source in files:
                    target = output / source.name
                    if target.exists():
                        shutil.copy2(target, backup / source.name)
                    os.replace(source, target)
                    changed.append(source.name)
                for name in retired_files:
                    target = output / name
                    if target.exists():
                        os.replace(target, backup / name)
                        changed.append(name)
            except BaseException:
                for name in reversed(changed):
                    old = backup / name
                    if old.exists():
                        os.replace(old, output / name)
                    else:
                        (output / name).unlink(missing_ok=True)
                raise
            (output / 'failed_refresh.md').unlink(missing_ok=True)
            (output / 'rejected_dashboard.html').unlink(missing_ok=True)
        print(f"SUCCESS: data date {snapshot['session_date']}; {len(snapshot['themes'])} eligible ETF anchors across {len(snapshot.get('registry_diagnostics', []))} registry records; {sum(len(t['selected']) for t in snapshot['themes'])} stock selections.")
        print(f"Open {output / 'dashboard.html'}\nDownload bundle: {output / 'run_bundle.zip'}")
        return 0
    except Exception as exc:
        output.mkdir(parents=True, exist_ok=True)
        preserved = False
        preserved_date = None
        if (output / 'dashboard.html').exists():
            try:
                old_snapshot = json.loads((output / 'latest_snapshot.json').read_text(encoding='utf-8'))
                old_raw = json.loads((output / 'raw_inputs.json').read_text(encoding='utf-8'))
                validate(enrich(old_snapshot, old_raw), old_raw)
                preserved = True
                preserved_date = old_snapshot.get("session_date")
            except Exception:
                # Retain an invalid old export for diagnosis without presenting it as usable.
                os.replace(output / 'dashboard.html', output / 'rejected_dashboard.html')
        status = {'status': 'failed', 'attempted_at': attempted, 'reason': str(exc), 'source_errors': raw.get('errors', {}), 'dashboard_preserved': preserved, 'preserved_data_date': preserved_date}
        _write_json(output / 'refresh_status.json', status)
        (output / 'failed_refresh.md').write_text(f"# Refresh failed\n\nAttempt: {attempted}\n\n{exc}\n\n" + ('Existing dashboard and its original date were preserved.' if preserved else 'No dashboard was generated. No successful snapshot exists in this directory.') + '\n', encoding='utf-8')
        print(f"GENERATION FAILED: {exc}\n" + ('Existing dashboard preserved with its original data date.' if preserved else 'No successful dashboard was generated.') + f"\nDetails: {output / 'refresh_status.json'}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
