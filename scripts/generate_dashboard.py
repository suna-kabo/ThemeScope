#!/usr/bin/env python3
"""Collect current public-source inputs and regenerate the static ThemeScope deliverables."""

from __future__ import annotations

import argparse
import base64
import copy
import csv
import gzip
import io
import json
import re
import sys
import zipfile
import tempfile
import time
import shutil
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.themescope.collect_v7 import build_snapshot_v7 as build_snapshot  # noqa: E402
from src.themescope.presentation import enrich, validate
from src.themescope.v5 import apply as apply_v5, apply_historical_ranks, map_iwm_universe, map_universe
from src.themescope.v6 import apply_v6, prepare_registry_themes
from src.themescope.metrics import return_metric, trend_metric
from src.themescope.watchlists import apply_watchlists  # noqa: E402
from src.themescope.release_audit import audit_release  # noqa: E402


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _write_bounded_json(path: Path, data: Any, maximum_bytes: int, artifact_name: str) -> None:
    encoded = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    size = len(encoded.encode("utf-8"))
    if size > maximum_bytes:
        raise ValueError(f"{artifact_name} is {size:,} bytes; configured limit is {maximum_bytes:,}. Reduce retained inputs or raise the corresponding maximum_*_bytes setting deliberately.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(encoded, encoding="utf-8")


def _clean_v7_output(value: Any) -> Any:
    """Strip retired v6 labels and subjective fields from compact v7 output."""
    if isinstance(value, dict):
        output = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text == "comparisons" or key_text.startswith("market_condition") or key_text.startswith("etf_breadth"):
                continue
            if key_text == "input_version" and str(item).startswith("themescope-v"):
                continue
            if key_text == "field_status" and isinstance(item, dict):
                item = {name: detail for name, detail in item.items() if not str(name).startswith("market_condition") and not str(name).startswith("etf_breadth")}
            output[key] = _clean_v7_output(item)
        return output
    if isinstance(value, list):
        return [cleaned for item in value if (cleaned := _clean_v7_output(item)) is not None]
    if isinstance(value, str) and "etf holdings breadth" in value.casefold():
        return None
    return value


def _dashboard_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Keep the offline UI payload small; detailed audit data remains downloadable."""
    payload = copy.deepcopy(snapshot)
    for key in ("candidate_metrics", "registry_diagnostics", "historical_rank_metrics", "source_matrix", "classification_catalog"):
        payload.pop(key, None)
    theme_internal = {
        "scope", "included", "excluded", "anchor_rationale", "anchor_url", "parent_sector",
        "representation_limit", "representation_status", "holdings_source", "holdings_age_days",
        "holdings_fresh", "holdings_breadth", "holdings_asof", "breadth_eligible_equity_count",
        "official_holdings_count", "official_unique_ticker_count",
        "duplicate_holding_ticker_rows", "evidence_reviewed_holdings_count", "reviewed_data_count",
        "eligible_reviewed_count", "pending_count", "excluded_count", "review_complete", "review_reason",
        "evidence_freshness_check_count", "stale_evidence_count", "unavailable_evidence_freshness_count",
        "unresolved_evidence_count", "pending_evidence_count", "anchor_screen", "parent_comparison",
        "reviewed_universe", "pending_holdings", "exclusions", "all_holdings", "source_error", "history",
        "curated_subset_breadth_diagnostic", "sector_member_exclusions", "stock_audit",
        "sector_membership_basis",
        "breadth_source_status", "breadth_source_reasons", "anchor_eligibility_status", "anchor_eligibility_reasons",
        "etf_breadth21_pct", "etf_breadth50_pct", "breadth21_t_minus_5", "breadth50_t_minus_5",
        "breadth21_change_5_pp", "breadth50_change_5_pp",
        "breadth_valid_ema21_count", "breadth_valid_ema50_count",
    }
    payload["themes"] = [
        {key: value for key, value in row.items() if key not in theme_internal}
        for row in snapshot.get("themes", [])
    ]
    for theme in payload["themes"]:
        theme["theme_watchlist_breadth"] = {
            period: {
                key: metric.get(key)
                for key in ("value", "status", "reason", "reason_code", "above_count", "valid_count", "eligible_count", "configured_count", "session_date", "ema_period")
            }
            for period, metric in theme.get("theme_watchlist_breadth", {}).items()
        }
    for market in payload.get("context", []):
        breadth = market.get("index_breadth")
        if isinstance(breadth, dict):
            for metric in breadth.values():
                if isinstance(metric, dict):
                    metric.pop("coverage_pct", None)
    return _clean_v7_output(payload)


def _ensure_v61_market_records(snapshot: dict[str, Any], raw: dict[str, Any], registry: dict[str, Any]) -> None:
    """Add explicit unavailable records when importing a pre-v6.1 real run."""
    session = snapshot.get('session_date')
    calendar = raw.get('session_calendar', [])
    context = {row.get('ticker'): row for row in snapshot.setdefault('context', [])}
    for symbol in registry.get('context_symbols', ['SPY', 'QQQ', 'IWM']):
        chart = raw.get('charts', {}).get(symbol)
        returns = {str(window): return_metric(chart, calendar, session, window) if chart else {'value': None, 'status': 'unavailable', 'reason': 'Price history was not included in this imported run'} for window in (5, 21, 63)}
        trend = trend_metric(chart, calendar, session, snapshot.get('settings', {})) if chart else {'state': 'Unavailable', 'status': 'unavailable', 'reason': 'Price history was not included in this imported run'}
        context.setdefault(symbol, {'ticker': symbol})
        context[symbol].setdefault('returns', returns)
        context[symbol].setdefault('trend', trend.get('state'))
        context[symbol].setdefault('trend_status', trend.get('status'))
        context[symbol].setdefault('trend_reason', trend.get('reason'))
        context[symbol].setdefault('source_url', chart.get('url') if chart else None)
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
        from src.themescope.v5 import map_iwm_universe
        v5 = raw.setdefault('v5', {})
        universes = v5.setdefault('index_universes', {})
        mapped = v5.setdefault('mapped_universes', {})
        security_mapping = v5.get('security_mapping', {})
        for symbol, source in context_holdings.items():
            universes[symbol] = source
            remapped = map_iwm_universe(source, security_mapping)
            if mapped.get(symbol, {}).get('price_collection'):
                remapped['price_collection'] = mapped[symbol]['price_collection']
            mapped[symbol] = remapped


def _restricted_registry(registry: dict[str, Any], active_config: dict[str, Any]) -> dict[str, Any]:
    """Keep the previously eligible anchors fixed through the v7 migration."""
    anchors = active_config.get('anchors', {})
    inactive = {row.get('theme_id'): row for row in active_config.get('inactive_records', [])}
    restricted = dict(registry)
    restricted['themes'] = []
    for record in registry.get('themes', []):
        item = dict(record)
        ticker = anchors.get(record.get('id'))
        item['candidate_anchors'] = [ticker] if ticker else []
        if ticker:
            item['anchor'] = ticker
        elif record.get('id') in inactive:
            item['_v7_preserved_inactive'] = inactive[record.get('id')]
        restricted['themes'].append(item)
    return restricted


def _retain_iwm_breadth(snapshot: dict[str, Any], raw: dict[str, Any], root: Path) -> None:
    """Persist the last successful IWM proxy breadth and label stale reuse."""
    if not raw.get('v7_mode'):
        return
    market = next((row for row in snapshot.get('context', []) if row.get('ticker') == 'IWM'), None)
    if not market:
        return
    path = root / 'cache' / 'aggregates' / 'iwm_breadth.json'
    try:
        previous = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        previous = {}
    current = market.get('index_breadth', {})
    complete = all(current.get(str(period), {}).get('status') == 'valid' for period in (21, 50))
    current_session = str(snapshot.get('session_date') or '')
    previous_session = str(previous.get('session_date') or '')
    if complete:
        if previous_session > current_session:
            market['index_breadth_observation_date'] = current_session
            market['index_breadth_stale'] = False
            return
        record = {
            'session_date': snapshot.get('session_date'),
            'breadth': {str(period): current[str(period)] for period in (21, 50)},
            'change_5_pp': {str(period): market.get(f'breadth{period}_change_5_pp') for period in (21, 50)},
            'saved_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(record, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
        os.replace(temp, path)
        market['index_breadth_observation_date'] = snapshot.get('session_date')
        market['index_breadth_stale'] = False
        return
    if not previous_session or previous_session > current_session or not all(previous.get('breadth', {}).get(str(period), {}).get('status') == 'valid' for period in (21, 50)):
        market['index_breadth_observation_date'] = current_session
        market['index_breadth_stale'] = False
        return
    reason = f"Current IWM breadth update failed; reusing the last successful observation from {previous['session_date']}."
    market['index_breadth'] = previous['breadth']
    market['index_breadth_observation_date'] = previous['session_date']
    market['index_breadth_stale'] = True
    for period in (21, 50):
        item = dict(previous['breadth'][str(period)])
        item.update({'stale': True, 'reason': reason, 'session_date': previous['session_date']})
        market['index_breadth'][str(period)] = item
        market[f'index_breadth{period}_pct'] = item.get('value')
        market[f'index_valid_ema{period}_count'] = item.get('valid_count')
        market[f'breadth{period}_change_5_pp'] = previous.get('change_5_pp', {}).get(str(period))
        market['field_status'][f'index_breadth{period}_pct'] = item
        market['field_status'][f'breadth{period}_change_5_pp'] = {'value': market[f'breadth{period}_change_5_pp'], 'status': 'valid' if market[f'breadth{period}_change_5_pp'] is not None else 'unavailable', 'reason': reason, 'session_date': previous['session_date'], 'stale': True}


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
    if raw.get('v7_mode'):
        configuration = raw.get('source_configuration', {})
        rows.append(dict(field='Market and watchlist price histories', scope='SPY, QQQ, IWM, active ETF anchors, configured members, VIX', provider='Yahoo Finance', method='Persistent compressed per-symbol cache; bounded incremental updates; chart API', as_of=snapshot.get('session_date'), retrieved_at=snapshot.get('collection_completed_at'), url=None, payload_kind='normalized_chart', payload_sha256=None, limitations='Histories are stored in compressed sidecars in the run bundle.'))
        for symbol, source in raw.get('v5', {}).get('index_universes', {}).items():
            rows.append(dict(field='Index constituent universe', scope=symbol, provider=configuration.get('index_constituents', {}).get(symbol, {}).get('provider'), method='Daily source snapshot; cached within session', as_of=source.get('effective_date') or source.get('observation_date') or source.get('as_of'), retrieved_at=source.get('retrieved_at'), url=source.get('url'), payload_kind='universe', payload_sha256=None, limitations='IWM holdings are a practical Russell 2000 proxy; SPY current constituent table is an observed list.'))
        stats = raw.get('price_cache_stats', {})
        rows.append(dict(field='Persistent cache activity', scope='Price histories', provider='Local cache', method=f"{stats.get('hits', 0)} hits; {stats.get('incremental_updates', 0)} incremental; {stats.get('full_refreshes', 0)} full; {stats.get('stale_reuses', 0)} stale reuses", as_of=snapshot.get('session_date'), retrieved_at=None, url=None, payload_kind='cache_statistics', payload_sha256=None, limitations='Cache files live under ignored cache/ and are not committed.'))
        return rows
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
    add('IWM eligible holdings price histories', 'Official iShares IWM equity holdings', 'Yahoo Finance', 'Direct normalized issuer tickers; one year per symbol; SEC CIK used for verification/deduplication, not as a price-download gate', next(iter(raw.get('v5', {}).get('iwm_breadth_charts', {}).values()), {}), 'Current iShares holdings are a Russell 2000 proxy, not an official Russell 2000 constituent feed. Full chart payloads are in iwm_breadth_prices.csv.gz.')
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


def _v7_run_report(snapshot: dict[str, Any], raw: dict[str, Any]) -> str:
    watchlists = raw.get('watchlists', {}).get('watchlists', [])
    by_id = {row.get('theme_id'): row for row in watchlists}
    theme_rows = snapshot.get('themes', [])
    active = len(theme_rows)
    final_statuses = {'complete', 'reviewed_short', 'reviewed_etf_only'}
    valid_records = [
        row for row in theme_rows
        if by_id.get(row.get('id'))
        and by_id[row['id']].get('anchor') == row.get('anchor')
        and by_id[row['id']].get('status') in final_statuses
    ]
    missing = [row for row in theme_rows if row not in valid_records]
    configured = [row for row in theme_rows if by_id.get(row.get('id')) and by_id[row['id']].get('anchor') == row.get('anchor')]
    memberships = [member for row in configured for member in by_id[row['id']].get('members', [])]
    counts = {}
    for member in memberships:
        counts[member['ticker']] = counts.get(member['ticker'], 0) + 1
    overlaps = {ticker: count for ticker, count in counts.items() if count > 1}
    diagnostics = snapshot.get('registry_diagnostics', [])
    inactive_exposures = [row for row in diagnostics if row.get('status') != 'selected_anchor']
    rejected_candidate_rows = sum(
        candidate.get('status') != 'eligible'
        for exposure in inactive_exposures
        for candidate in exposure.get('candidates', [])
    )
    status_counts = {
        status: sum(by_id[row['id']].get('status') == status for row in valid_records)
        for status in ('complete', 'reviewed_short', 'reviewed_etf_only')
    }
    valid21 = sum(row.get('theme_breadth21_pct') is not None and row.get('theme_breadth21_valid') is not None for row in theme_rows)
    valid50 = sum(row.get('theme_breadth50_pct') is not None and row.get('theme_breadth50_valid') is not None for row in theme_rows)
    cache = raw.get('price_cache_stats', {})
    requests = raw.get('collection_request_counts', {})
    cache_line = (
        f"- Offline bundle: {cache.get('offline_import_histories_reused', 0):,} saved price histories reused; no cache fetches were attempted."
        if cache.get('offline_import_histories_reused') is not None else
        f"- Persistent cache: {cache.get('hits', 0):,} hits; {cache.get('incremental_updates', 0)} incremental updates; {cache.get('full_refreshes', 0)} full refreshes; {cache.get('failures', 0)} failures; {cache.get('stale_reuses', 0)} stale series reused."
    )
    lines = [
        '# ThemeScope v7.1 run report', '',
        f"Market session: {snapshot.get('session_date')}", '',
        f"Dashboard generated: {snapshot.get('dashboard_generated_at') or snapshot.get('generated_at')}", '',
        f"Workflow: {'offline import / rerender' if requests.get('price_history') == 0 and requests.get('universe') == 0 else 'normal cached market refresh'}",
        '', '## Ranking and state', '',
        'Current is the percentile rank of 21-session ETF excess return versus SPY. Medium is the 63-session percentile. Theme Score remains `0.60 × Current + 0.40 × Medium`, with the configured 50 state threshold. Theme and index breadth do not affect score, state, or rank.',
        '', '## Watchlist configuration', '',
        f"- Active exposures: {active}; inactive exposures: {len(inactive_exposures)}; rejected candidate ETF rows: {rejected_candidate_rows}.",
        f"- Final reviewed lists: {len(valid_records)}/{active} (complete {status_counts['complete']}; reviewed short {status_counts['reviewed_short']}; reviewed ETF-only {status_counts['reviewed_etf_only']}); stored records {len(watchlists)}.",
        f"- Configured memberships: {len(memberships)}; unique stocks: {len(counts)}; overlapping stocks: {len(overlaps)} ({sum(n - 1 for n in overlaps.values())} additional memberships).",
        f"- Themes with valid EMA21 breadth: {valid21}; with valid EMA50 breadth: {valid50}.",
        '- Lists: ' + (', '.join(f"{row['name']} ({len(by_id[row['id']]['members'])}, {by_id[row['id']].get('status', 'not reviewed')})" for row in configured) or 'none') + '.',
        '- Release audit: ' + ('PASS' if not missing else f"BLOCKED; {len(missing)} active exposure records are missing final review: " + ', '.join(f"{row['name']} ({row['id']})" for row in missing)) + '.',
        '', '## Cache and requests', '',
        cache_line,
        f"- Source requests by category: price histories {requests.get('price_history', 0)}; index universes {requests.get('universe', 0)}; filings {requests.get('filings', 0)}; company quotes {requests.get('quotes', 0)}; theme holdings {requests.get('theme_holdings', 0)}; AUM/spread {requests.get('aum_spread', 0)}.",
        '- A rerender/import uses no network requests. Request totals shown here count actual collector fetches, not cache hits.',
        '', '## Breadth and limits', '',
        '- Theme breadth uses the fixed configured list and displays above/valid counts. Validity requires at least 8 observations and at least 80% of configured members. A missing ticker stays in the configured denominator.',
        '- Five-session breadth change uses the same current membership at both dates; it is not a historical point-in-time universe.',
        '- Index breadth remains separate: SPY uses observed S&P 500 constituents, QQQ uses Nasdaq-100, and IWM uses current holdings as a practical Russell 2000 proxy.',
        '- A release requires one reviewed configuration record for each active exposure; incomplete records block publishing and are not represented as awaiting a future CSV.',
        '- Normal refresh reads the approved static membership and does not run classification research, full ETF holdings breadth, AUM, spreads, or daily market-cap requests.',
        '', '## Files', '',
        'The run bundle includes the dashboard, compact snapshot and CSVs, configuration, and compressed price sidecars. Run `python3 scripts/generate_dashboard.py --import-run output` to rerender without network access.',
    ]
    return '\n'.join(lines) + '\n'


def _watchlist_migration_report(snapshot: dict[str, Any], raw: dict[str, Any]) -> str:
    report = _v7_run_report(snapshot, raw)
    section = report[report.index('## Watchlist configuration'):report.index('## Cache and requests')]
    return '# ThemeScope v7.1 watchlist review\n\n' + section


EXPORT_COLUMNS = [
    "theme", "theme_id", "anchor", "session_date", "generated_at", "selection_slot",
    "ticker", "company", "exchange", "membership_tag", "membership_rationale", "price_close",
    "return5_pct", "excess5_pp", "return21_pct", "excess21_pp", "return63_pct", "excess63_pp",
    "above_ema21", "above_ema50", "ema21", "ema50", "adv30_usd", "market_cap_usd",
    "relative_state", "price_trend", "chart_url",
]


def _number(metric: dict[str, Any] | None) -> float | None:
    if not metric or metric.get("status") != "valid":
        return None
    return metric.get("value")


def _theme_csv_row(record: dict[str, Any]) -> dict[str, Any]:
    """Flatten only the user-facing ranking and configured breadth fields."""
    row = {
        'rank_current': record.get('rank_current', record.get('global_rank')),
        'rank_t_minus_5': record.get('rank_t_minus_5'),
        'rank_change_5': record.get('rank_change_5'),
        'type': 'Sector' if record.get('level') == 'Sector' else 'Theme',
        'theme_id': record.get('id'),
        'name': record.get('name'),
        'anchor_etf': record.get('anchor'),
        'state': record.get('theme_state'),
        'research_priority': record.get('research_priority', {}).get('label'),
        'theme_score': record.get('theme_score'),
        'current_strength': record.get('current_strength_score'),
        'medium_strength': record.get('medium_strength_score'),
        'configured_watchlist_count': record.get('configured_watchlist_count', 0),
        'session_date': record.get('session_date'),
        'generated_at': record.get('dashboard_generated_at') or record.get('generated_at'),
    }
    value = _number(record.get('returns', {}).get('5'))
    row['return5_pct'] = value * 100 if value is not None else None
    value = _number(record.get('excess_returns', {}).get('5'))
    row['excess5_pp'] = value * 100 if value is not None else None
    for window in ('21', '63'):
        value = _number(record.get('returns', {}).get(window))
        row[f'return{window}_pct'] = value * 100 if value is not None else None
        value = _number(record.get('excess_returns', {}).get(window))
        row[f'excess{window}_pp'] = value * 100 if value is not None else None
    for period in (21, 50):
        breadth = record.get('theme_watchlist_breadth', {}).get(str(period), {})
        row[f'theme_breadth{period}_pct'] = breadth.get('value')
        row[f'theme_breadth{period}_above'] = breadth.get('above_count')
        row[f'theme_breadth{period}_valid'] = breadth.get('valid_count')
        row[f'theme_breadth{period}_change_5_pp'] = breadth.get('change_5_pp')
    return row


THEME_EXPORT_COLUMNS = [
    'rank_current', 'rank_t_minus_5', 'rank_change_5', 'type', 'theme_id', 'name', 'anchor_etf',
    'state', 'research_priority', 'theme_score', 'current_strength', 'medium_strength', 'return21_pct', 'excess21_pp',
    'return63_pct', 'excess63_pp', 'theme_breadth21_pct', 'theme_breadth21_above', 'theme_breadth21_valid',
    'theme_breadth21_change_5_pp', 'theme_breadth50_pct', 'theme_breadth50_above', 'theme_breadth50_valid',
    'theme_breadth50_change_5_pp', 'configured_watchlist_count', 'session_date', 'generated_at',
]

MARKET_EXPORT_COLUMNS = [
    'ticker', 'name', 'instrument_type', 'session_date', 'price_close', 'daily_change_pct',
    'return5_pct', 'return21_pct', 'return63_pct', 'ema21', 'ema50', 'above_ema21', 'above_ema50',
    'index_breadth21_pct', 'index_breadth21_above_count', 'index_breadth21_valid_count',
    'index_breadth21_eligible_count', 'breadth21_change_5_pp', 'index_breadth50_pct',
    'index_breadth50_above_count', 'index_breadth50_valid_count', 'index_breadth50_eligible_count',
    'breadth50_change_5_pp', 'level', 'trailing_1y_percentile', 'vix_direction_1d',
    'vix_direction_5d', 'vix_direction_21d', 'generated_at',
]


def _market_csv_row(record: dict[str, Any], session: str, generated_at: str) -> dict[str, Any]:
    row = {key: record.get(key) for key in ('ticker', 'name', 'instrument_type', 'price_close', 'ema21', 'ema50', 'above_ema21', 'above_ema50', 'level', 'trailing_1y_percentile', 'vix_direction_1d', 'vix_direction_5d', 'vix_direction_21d')}
    row['session_date'] = session
    row['generated_at'] = generated_at
    daily = record.get('daily_change')
    row['daily_change_pct'] = daily * 100 if isinstance(daily, (int, float)) else None
    for window in (5, 21, 63):
        value = _number(record.get('returns', {}).get(str(window)))
        row[f'return{window}_pct'] = value * 100 if value is not None else (record.get(f'return{window}') * 100 if isinstance(record.get(f'return{window}'), (int, float)) else None)
    for period in (21, 50):
        breadth = record.get('index_breadth', {}).get(str(period), {})
        row[f'index_breadth{period}_pct'] = breadth.get('value')
        row[f'index_breadth{period}_above_count'] = breadth.get('above_count')
        row[f'index_breadth{period}_valid_count'] = breadth.get('valid_count')
        row[f'index_breadth{period}_eligible_count'] = breadth.get('eligible_count')
        row[f'breadth{period}_change_5_pp'] = record.get(f'breadth{period}_change_5_pp')
    return row


def _all_selected(snapshot: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    rows = []
    for theme in snapshot.get("themes", []):
        for stock in sorted(theme.get("selected", []), key=lambda row: row.get("selection_slot", 10**9))[:limit]:
            exchange = str(stock.get("exchange") or "").upper()
            prefix = "NASDAQ" if exchange.startswith("NASDAQ") else ("NYSE" if exchange.startswith("NYSE") else "")
            chart_url = f"https://www.tradingview.com/chart/?symbol={prefix}:{stock['ticker']}" if prefix else None
            rows.append({
                **{key: stock.get(key) for key in ('membership_tag','membership_rationale','price_close','ema21','ema50')},
                'return5_pct': (value * 100 if (value := _number(stock.get('returns', {}).get('5'))) is not None else None),
                'excess5_pp': (value*100 if (value := _number(stock.get('excess_returns', {}).get('5'))) is not None else None),
                'above_ema21': stock.get('price_close') > stock['ema21'] if stock.get('price_close') is not None and stock.get('ema21') is not None else None,
                'above_ema50': stock.get('price_close') > stock['ema50'] if stock.get('price_close') is not None and stock.get('ema50') is not None else None,
                "theme": theme["name"], "theme_id": theme["id"], "anchor": theme["anchor"],
                "selection_slot": stock.get("selection_slot"),
                "ticker": stock.get("ticker"), "company": stock.get("company"), "exchange": stock.get("exchange"),
                "market_cap_usd": stock.get("market_cap_usd"),
                "market_cap_retrieved_at": stock.get("market_cap_retrieved_at"), "adv30_usd": stock.get("adv30_usd"),
                "return21_pct": (value * 100 if (value := _number(stock.get("returns", {}).get("21"))) is not None else None),
                "return63_pct": (value * 100 if (value := _number(stock.get("returns", {}).get("63"))) is not None else None),
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


def _write_iwm_sidecar(path: Path, charts: dict[str, Any]) -> None:
    """Keep the broad IWM price universe outside raw_inputs.json's GitHub 100 MB cap."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("symbol", "chart_json"), lineterminator="\n")
        writer.writeheader()
        for symbol, chart in sorted(charts.items()):
            writer.writerow({"symbol": symbol, "chart_json": json.dumps(chart, separators=(",", ":"), ensure_ascii=False, allow_nan=False)})


def _load_iwm_sidecar(raw: dict[str, Any], content: bytes) -> None:
    charts = {}
    with gzip.GzipFile(fileobj=io.BytesIO(content), mode="rb") as compressed:
        with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                charts[row["symbol"]] = json.loads(row["chart_json"])
    raw.setdefault("v5", {})["iwm_breadth_charts"] = charts


def _load_chart_sidecar(raw: dict[str, Any], content: bytes, key: str) -> None:
    charts = {}
    with gzip.GzipFile(fileobj=io.BytesIO(content), mode="rb") as compressed:
        with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                charts[row["symbol"]] = json.loads(row["chart_json"])
    raw.setdefault("v5", {}).setdefault("charts", {}).update(charts)
    raw.setdefault("v5", {}).setdefault("chart_sidecars_loaded", []).append(key)


def _rehydrate_index_universes(raw: dict[str, Any]) -> None:
    """Rebuild compact SPY/QQQ ticker maps from retained constituent rows."""
    v5 = raw.setdefault('v5', {})
    mapped = v5.setdefault('mapped_universes', {})
    universes = v5.get('index_universes', {})
    for symbol in ('SPY', 'QQQ'):
        if mapped.get(symbol, {}).get('companies'):
            continue
        source = universes.get(symbol, {})
        listings = {}
        for row in source.get('rows', []):
            ticker = str(row.get('ticker') or '').strip().upper()
            country = str(row.get('country') or '').strip().casefold()
            security_id = str(row.get('security_id') or '')
            if not ticker or (country and country != 'united states' and not security_id.startswith('US')):
                continue
            normalized = ticker.replace('.', '-')
            if re.fullmatch(r'[A-Z][A-Z0-9-]{0,14}', normalized):
                # Compact imports can omit SEC CIKs. Retain the source's stable
                # issuer id when available, otherwise keep each ticker distinct.
                listings[ticker] = {'ticker': normalized, 'cik': row.get('company_id') or ticker}
        mapped[symbol] = map_universe(source, {'listings': listings}, index=True)
    if not mapped.get('IWM', {}).get('companies') and universes.get('IWM', {}).get('rows'):
        mapped['IWM'] = map_iwm_universe(universes['IWM'], {})


def _retain_imported_index_metrics(snapshot: dict[str, Any], imported_context: list[dict[str, Any]]) -> None:
    """Keep saved current breadth while adding newly computable fixed-universe changes."""
    imported = {row.get('ticker'): row for row in imported_context}
    for market in snapshot.get('context', []):
        previous = imported.get(market.get('ticker'))
        if not previous or not isinstance(previous.get('index_breadth'), dict):
            continue
        old_breadth = previous['index_breadth']
        new_field_status = market.setdefault('field_status', {})
        market['index_breadth'] = copy.deepcopy(old_breadth)
        for period in (21, 50):
            key = str(period)
            old_metric = old_breadth.get(key, {})
            market[f'index_breadth{period}_pct'] = old_metric.get('value')
            market[f'index_valid_ema{period}_count'] = old_metric.get('valid_count')
            market[f'index_coverage{period}_pct'] = old_metric.get('coverage_pct')
            new_field_status[f'index_breadth{period}_pct'] = copy.deepcopy(old_metric)
            previous_value = previous.get(f'breadth{period}_t_minus_5')
            previous_change = previous.get(f'breadth{period}_change_5_pp')
            if previous_value is None:
                calculated_prior = new_field_status.get(f'breadth{period}_t_minus_5', {})
                current_value = old_breadth.get(key, {}).get('value')
                prior_value = calculated_prior.get('value') if calculated_prior.get('status') == 'valid' else None
                calculated_change = current_value - prior_value if isinstance(current_value, (int, float)) and isinstance(prior_value, (int, float)) else None
                market[f'breadth{period}_t_minus_5'] = prior_value
                market[f'breadth{period}_change_5_pp'] = calculated_change
                new_field_status[f'breadth{period}_t_minus_5'] = calculated_prior
                new_field_status[f'breadth{period}_change_5_pp'] = {
                    'value': calculated_change,
                    'status': 'valid' if calculated_change is not None else 'unavailable',
                    'reason': None if calculated_change is not None else calculated_prior.get('reason') or 'Five-session-prior breadth is unavailable.',
                    'session_date': snapshot.get('session_date'),
                    'universe_method': 'fixed current constituent/proxy universe at both price dates',
                }
            else:
                market[f'breadth{period}_t_minus_5'] = previous_value
                market[f'breadth{period}_change_5_pp'] = previous_change


def _write_chart_sidecar(path: Path, charts: dict[str, Any]) -> None:
    _write_iwm_sidecar(path, charts)


def _primary_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Keep calculated facts and compact configured rows, excluding diagnostics."""
    payload = dict(snapshot)
    for key in ('candidate_metrics', 'registry_diagnostics', 'historical_rank_metrics', 'source_matrix', 'classification_catalog'):
        payload.pop(key, None)
    theme_fields = {
        'id', 'name', 'level', 'anchor', 'chart_url', 'returns', 'excess_returns', 'relative_state', 'trend',
        'trend_status', 'ema21', 'ema50', 'ema21_slope_5', 'price_close', 'daily_change', 'ema21_distance',
        'ema50_distance', 'price_vs_ema21_pct', 'price_vs_ema50_pct', 'above_ema21', 'above_ema50',
        'price_status', 'price_reason', 'price_session_date', 'price_source_url', 'price_retrieved_at',
        'relative_strength_series', 'theme_breadth21_pct', 'theme_breadth21_above', 'theme_breadth21_valid',
        'theme_breadth21_change_5_pp', 'theme_breadth21_t_minus_5', 'theme_breadth50_pct',
        'theme_breadth50_above', 'theme_breadth50_valid', 'theme_breadth50_change_5_pp', 'theme_breadth50_t_minus_5',
        'current_strength_score',
        'medium_strength_score', 'theme_score', 'theme_state', 'score_method', 'score_peer_count_21',
        'score_peer_count_63', 'score_unavailable_reason', 'global_rank', 'rank_current', 'rank_t_minus_5',
        'rank_change_5', 'historical_rank_peer_count', 'historical_rank_status', 'historical_rank_reason',
        'historical_rank_session', 'theme_watchlist_breadth', 'watchlist_reviewed_date', 'configured_watchlist_count',
        'watchlist_status', 'watchlist_exception_reason', 'watchlist_list_rationale', 'reviewed_candidate_count',
        'watchlist_unavailable_reason', 'watchlist_version', 'has_watchlist',
        'watchlist_member_count', 'stock_scope', 'stock_drilldown_status', 'session_date',
    }
    stock_fields = {
        'ticker', 'company', 'exchange', 'relationship', 'membership_tag', 'membership_rationale',
        'membership_source', 'reviewed_date', 'theme_id', 'theme_name', 'anchor', 'price_close', 'adv30_usd',
        'market_cap_usd', 'market_cap_retrieved_at', 'ema21', 'ema50', 'above_ema21', 'above_ema50',
        'trend', 'returns', 'excess_returns', 'session_date', 'price_status', 'selection_slot', 'selection_queue',
    }
    themes = []
    for row in snapshot.get('themes', []):
        compact = {key: value for key, value in row.items() if key in theme_fields}
        compact['returns'] = {key: {'value': item.get('value'), 'status': item.get('status')} for key, item in row.get('returns', {}).items()}
        compact['excess_returns'] = {key: {'value': item.get('value'), 'status': item.get('status')} for key, item in row.get('excess_returns', {}).items()}
        compact['theme_watchlist_breadth'] = {
            period: {key: metric.get(key) for key in ('value', 'status', 'reason', 'reason_code', 'above_count', 'valid_count', 'eligible_count', 'configured_count', 'session_date', 'ema_period', 't_minus_5', 'change_5_pp', 'prior_session', 'change_reason')}
            for period, metric in row.get('theme_watchlist_breadth', {}).items()
        }
        compact['selected'] = [{
            **{key: value for key, value in stock.items() if key in stock_fields and key not in ('returns', 'excess_returns')},
            'returns': {key: {'value': item.get('value'), 'status': item.get('status')} for key, item in stock.get('returns', {}).items()},
            'excess_returns': {key: {'value': item.get('value'), 'status': item.get('status')} for key, item in stock.get('excess_returns', {}).items()},
        } for stock in row.get('selected', [])]
        themes.append(compact)
    payload['themes'] = themes
    for context in payload.get('context', []):
        breadth = context.get('index_breadth')
        if isinstance(breadth, dict):
            breadth.pop('companies', None)
            for metric in breadth.values():
                if isinstance(metric, dict):
                    metric.pop('companies', None)
        context.pop('fields', None)
        context.pop('history', None)
    payload.pop('comparisons', None)
    return _clean_v7_output(payload)


def _compact_raw(raw: dict[str, Any], snapshot: dict[str, Any], sidecars: dict[str, int]) -> dict[str, Any]:
    """Keep primary raw JSON small; all price histories remain in run sidecars."""
    output = dict(raw)
    core_symbols = {row.get('anchor') for row in snapshot.get('themes', [])}
    core_symbols |= {row.get('ticker') for row in snapshot.get('context', [])}
    core_symbols |= {row.get('ticker') for row in snapshot.get('volatility_context', [])}
    output['charts'] = {key: value for key, value in raw.get('charts', {}).items() if key in core_symbols}
    output['errors'] = {'charts': raw.get('errors', {}).get('charts', {})}
    for key in ('holdings', 'comparison_holdings', 'context_holdings', 'quotes', 'sec_annual_checks', 'evidence_freshness', 'cache_manifest'):
        output.pop(key, None)
    output.pop('v7_registry', None)
    v5 = dict(raw.get('v5', {}))
    v5.pop('charts', None)
    v5.pop('iwm_breadth_charts', None)
    v5.pop('security_mapping', None)
    for key in ('holdings', 'mapped_universes', 'iwm_breadth_diagnostics', 'chart_sidecars_loaded'):
        v5.pop(key, None)
    for key in ('index_universes',):
        original = v5.get(key, {})
        v5[key] = {symbol: value for symbol, value in original.items() if symbol in {'SPY', 'QQQ', 'IWM'}}
    v5['market_breadth_sidecar'] = {'file': 'market_breadth_prices.csv.gz', 'chart_count': sidecars.get('market', 0), 'encoding': 'gzip CSV; normalized chart JSON per symbol'}
    v5['watchlist_price_sidecar'] = {'file': 'watchlist_prices.csv.gz', 'chart_count': sidecars.get('watchlist', 0), 'encoding': 'gzip CSV; normalized chart JSON per symbol'}
    v5['iwm_breadth_sidecar'] = {'file': 'iwm_breadth_prices.csv.gz', 'chart_count': sidecars.get('iwm', 0), 'encoding': 'gzip CSV; normalized chart JSON per symbol'}
    output['v5'] = v5
    return output


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
    return (",".join(symbols) + ("\n" if symbols else ""), {"unique": len(symbols), "omitted": omitted, "duplicates": duplicates})


def _stock_diagnostics(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    if snapshot.get('schema_version') == '7.1':
        output = []
        for exposure in snapshot.get('themes', []):
            for row in exposure.get('selected', []):
                maintenance = row.get('maintenance') or {}
                output.append({
                    'theme_id': exposure.get('id'), 'theme': exposure.get('name'), 'anchor': exposure.get('anchor'),
                    'ticker': row.get('ticker'), 'relationship': row.get('relationship'),
                    'reason': row.get('membership_rationale'), 'exchange': row.get('exchange'),
                    'configuration_status': exposure.get('watchlist_status'),
                    'maintenance_date': maintenance.get('date'), 'candidate_source': maintenance.get('source_type'),
                    'maintenance_price_usd': maintenance.get('price_usd'),
                    'maintenance_market_cap_usd': maintenance.get('market_cap_usd'),
                    'maintenance_adv30_usd': maintenance.get('adv30_usd'),
                    'adjusted_price_sessions': maintenance.get('adjusted_price_sessions'),
                    'price_status': row.get('price_status'), 'price_close': row.get('price_close'),
                    'adv30_usd': row.get('adv30_usd'), 'market_cap_usd': row.get('market_cap_usd'),
                    'return5_pct': (100 * value if (value := _number(row.get('returns', {}).get('5'))) is not None else None),
                    'excess5_pp': (100 * value if (value := _number(row.get('excess_returns', {}).get('5'))) is not None else None),
                    'return21_pct': (100 * value if (value := _number(row.get('returns', {}).get('21'))) is not None else None),
                    'excess21_pp': (100 * value if (value := _number(row.get('excess_returns', {}).get('21'))) is not None else None),
                    'return63_pct': (100 * value if (value := _number(row.get('returns', {}).get('63'))) is not None else None),
                    'excess63_pp': (100 * value if (value := _number(row.get('excess_returns', {}).get('63'))) is not None else None),
                    'above_ema21': row.get('above_ema21'), 'above_ema50': row.get('above_ema50'),
                    'session_date': row.get('session_date') or snapshot.get('session_date'),
                })
        return output
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
                'return5_pct': (100 * value if (value := _number(row.get('returns', {}).get('5'))) is not None else None),
                'excess5_pp': (100 * value if (value := _number(row.get('excess_returns', {}).get('5'))) is not None else None),
                'return21_pct': (100 * value if (value := _number(row.get('returns', {}).get('21'))) is not None else None),
                'return63_pct': (100 * value if (value := _number(row.get('returns', {}).get('63'))) is not None else None),
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


def _theme_watchlist_summary(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for theme in snapshot.get('themes', []):
        rows.append({
            'theme_id': theme.get('id'),
            'name': theme.get('name'),
            'anchor': theme.get('anchor'),
            'status': theme.get('watchlist_status'),
            'member_count': theme.get('configured_watchlist_count', 0),
            'reviewed_candidate_count': theme.get('reviewed_candidate_count'),
            'exception_reason': theme.get('watchlist_exception_reason'),
            'theme_breadth21_pct': theme.get('theme_breadth21_pct'),
            'theme_breadth21_above': theme.get('theme_breadth21_above'),
            'theme_breadth21_valid': theme.get('theme_breadth21_valid'),
            'theme_breadth21_change_5_pp': theme.get('theme_breadth21_change_5_pp'),
            'theme_breadth50_pct': theme.get('theme_breadth50_pct'),
            'theme_breadth50_above': theme.get('theme_breadth50_above'),
            'theme_breadth50_valid': theme.get('theme_breadth50_valid'),
            'theme_breadth50_change_5_pp': theme.get('theme_breadth50_change_5_pp'),
        })
    return rows


def _membership_review_rows(config: dict[str, Any], themes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Export the approved assignments and their review evidence, not runtime diagnostics."""
    names = {row.get('id'): row.get('name') for row in themes}
    rows = []
    for watchlist in config.get('watchlists', []):
        for member in watchlist.get('members', []):
            maintenance = member.get('maintenance') if isinstance(member.get('maintenance'), dict) else {}
            rows.append({
                'theme_id': watchlist.get('theme_id'), 'theme': names.get(watchlist.get('theme_id')),
                'anchor': watchlist.get('anchor'), 'status': watchlist.get('status'),
                'reviewed_candidate_count': watchlist.get('reviewed_candidate_count'),
                'exception_reason': watchlist.get('exception_reason'),
                'list_rationale': watchlist.get('list_rationale'),
                'ticker': member.get('ticker'), 'company': member.get('company'),
                'exchange': member.get('exchange'), 'instrument_type': member.get('instrument_type'),
                'relationship': member.get('relationship'), 'reason': member.get('reason'),
                'maintenance_date': maintenance.get('date'), 'candidate_source': maintenance.get('source_type'),
                'price_usd': maintenance.get('price_usd'), 'market_cap_usd': maintenance.get('market_cap_usd'),
                'adv30_usd': maintenance.get('adv30_usd'),
                'adjusted_price_sessions': maintenance.get('adjusted_price_sessions'),
                'history_source': maintenance.get('adjusted_price_history_source'),
                'history_as_of': maintenance.get('adjusted_price_history_as_of'),
                'source_url': member.get('source_url'), 'reason_source_url': member.get('reason_source_url'),
            })
    return rows


def _run_report(snapshot: dict[str, Any], raw: dict[str, Any], matrix: list[dict[str, Any]], tv15: dict[str, int], tv20: dict[str, int]) -> str:
    lines = ['# ThemeScope v6.2 run report', '', f"Market session: {snapshot['session_date']}", f"Dashboard generated: {snapshot.get('dashboard_generated_at')} ({snapshot.get('dashboard_generated_at_hkt_display')})", f"Latest source retrieval: {snapshot.get('last_source_retrieved_at') or snapshot.get('collection_completed_at')}", f"Base collection: {snapshot.get('collection_started_at')} to {snapshot.get('collection_completed_at')}", f"Requested as-of: {snapshot.get('requested_asof') or 'latest verified completed common session'}", '', '## Market/index facts']
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
            lines.append(f"  - Close {relation} EMA{period} ({row.get('ema' + str(period))}); {breadth_label} {m.get('above_count')}/{m.get('valid_count')} valid, {m.get('eligible_count')} eligible, holdings/list as of {m.get('as_of')}; {m.get('status', 'unavailable')}: {m.get('reason') or 'valid'}; t-5 {row.get(f'breadth{period}_t_minus_5')}; change {row.get(f'breadth{period}_change_5_pp')} pp.")
    iwm_diag = raw.get('v5', {}).get('iwm_breadth_diagnostics', {})
    iwm_universe = raw.get('v5', {}).get('mapped_universes', {}).get('IWM', {})
    iwm_price_collection = iwm_universe.get('price_collection', {})
    iwm_market = next((row for row in snapshot.get('context', []) if row.get('ticker') == 'IWM'), {})
    iwm_shortfalls = iwm_diag.get('history_shortfalls', iwm_price_collection.get('history_shortfall_details', {}))
    shortfall_sample = ', '.join(f'{ticker} {count}' for ticker, count in sorted(iwm_shortfalls.items())[:8])
    if len(iwm_shortfalls) > 8:
        shortfall_sample += f", +{len(iwm_shortfalls) - 8} more"
    retained_histories = iwm_diag.get('downloaded_histories', iwm_price_collection.get('downloaded_history_count', len(raw.get('v5', {}).get('iwm_breadth_charts', {}))))
    reused_histories = iwm_diag.get('reused_histories', iwm_price_collection.get('existing_history_reused', 0))
    new_history_responses = max(0, retained_histories - reused_histories)
    iwm_retrieval_errors = raw.get('v5', {}).get('iwm_breadth_errors', {})
    lines += ['', '## IWM holdings breadth collection',
        f"- Classification: {iwm_diag.get('source_rows', iwm_universe.get('source_row_count', 0))} source rows; {iwm_diag.get('classified_equity_rows', iwm_universe.get('classified_equity_rows', 0))} rows labeled Equity; {iwm_diag.get('issuer_description_exclusions', iwm_universe.get('issuer_description_exclusions', 0))} description exclusions; {iwm_diag.get('excluded_source_rows', len(iwm_universe.get('excluded_rows', [])))} total excluded.",
        f"- Ticker normalization/mapping: {iwm_diag.get('normalization_failures', iwm_universe.get('normalization_failure_count', 0))} normalization failures; {iwm_diag.get('eligible_equity_rows', iwm_universe.get('eligible_equity_rows', 0))} normalized equity rows; {iwm_diag.get('normalized_symbols', iwm_universe.get('normalized_symbol_count', 0))} unique symbols; {iwm_diag.get('sec_verified_companies', iwm_universe.get('sec_verified_company_count', 0))} SEC CIK matched; {iwm_diag.get('direct_ticker_companies', iwm_universe.get('direct_ticker_company_count', 0))} direct ticker fallback.",
        f"- History collection: {reused_histories} reused; {iwm_diag.get('new_requests', iwm_price_collection.get('new_requests', 0))} requested; {new_history_responses} new responses; {retained_histories} histories retained; {iwm_diag.get('history_qualified', iwm_price_collection.get('history_qualified_count', 0))} met the {iwm_diag.get('minimum_history_sessions', 205)}-session t-5 warmup; {len(iwm_shortfalls)} short histories{(': ' + shortfall_sample) if shortfall_sample else ''}; {len(iwm_retrieval_errors)} retrieval errors.",
        f"- EMA observations: EMA21 {iwm_market.get('index_breadth', {}).get('21', {}).get('valid_count', 0)}/{iwm_market.get('index_breadth', {}).get('21', {}).get('eligible_count', 0)}; EMA50 {iwm_market.get('index_breadth', {}).get('50', {}).get('valid_count', 0)}/{iwm_market.get('index_breadth', {}).get('50', {}).get('eligible_count', 0)}. The 80% completeness rule remains in force.",
        f"- EMA21 breadth: {iwm_market.get('index_breadth', {}).get('21', {}).get('status', 'unavailable')}; {iwm_market.get('index_breadth', {}).get('21', {}).get('reason') or 'valid'}.",
        f"- EMA50 breadth: {iwm_market.get('index_breadth', {}).get('50', {}).get('status', 'unavailable')}; {iwm_market.get('index_breadth', {}).get('50', {}).get('reason') or 'valid'}." ]
    if iwm_retrieval_errors:
        lines += ['', 'IWM history retrieval errors:']
        for ticker, reason in sorted(iwm_retrieval_errors.items()):
            status = re.search(r'HTTP Error \d+: [^;]+', str(reason))
            detail = status.group(0) if status else str(reason)[:180]
            lines.append(f"- {ticker}: {detail}; no chart returned by either Yahoo host.")
    lines += ['', '## Volatility context']
    for item in snapshot.get('volatility_context', []):
        lines.append(f"- {item.get('ticker')}: level {item.get('level')}; daily {item.get('daily_change')} ({item.get('vix_direction_1d')}); 5-session {item.get('return5')} ({item.get('vix_direction_5d')}); 21-session {item.get('return21')} ({item.get('vix_direction_21d')}); trailing 252-session percentile {item.get('trailing_1y_percentile')}; direction {item.get('vix_direction_summary')}; observation date {item.get('observation_date')}; retrieved {item.get('retrieved_at')}; {item.get('source_status')}: {item.get('source_reason') or item.get('source_url') or 'valid'}.")
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
        lines.append(f"- {row['name']} ({row['anchor']}), {row.get('level')}: score {row.get('theme_score')}; state {row.get('theme_state')}; current rank {row.get('rank_current', row.get('global_rank'))}; t-5 rank {row.get('rank_t_minus_5')}; rank change {row.get('rank_change_5')}; historical peers {row.get('historical_rank_peer_count')}; curated stock drilldown {drilldown}; anchor eligibility {candidate.get('status', 'eligible')}.")
        for field in ('percentile_excess21','percentile_excess63','etf_breadth21_pct','etf_breadth50_pct','current_strength_score','medium_strength_score','theme_score'):
            item = row.get('field_status', {}).get(field, {})
            lines.append(f"  - {field}: {row.get(field)}; {item.get('status')}; {item.get('reason') or 'valid'}")
        lines.append(f"  - Score peers: 21-session {row.get('score_peer_count_21')}; 63-session {row.get('score_peer_count_63')}; method {row.get('score_method')}; unavailable reason {row.get('score_unavailable_reason') or 'none'}.")
        lines.append(f"  - Breadth: EMA21 {row.get('breadth_status_21')}: {row.get('breadth_unavailable_reason_21') or 'valid'}; t-5 {row.get('breadth21_t_minus_5')}; change {row.get('breadth21_change_5_pp')} pp. EMA50 {row.get('breadth_status_50')}: {row.get('breadth_unavailable_reason_50') or 'valid'}; t-5 {row.get('breadth50_t_minus_5')}; change {row.get('breadth50_change_5_pp')} pp.")
        universe = raw.get('v5', {}).get('mapped_universes', {}).get(row['anchor'], {})
        lines.append(f"  - {len(universe.get('excluded_rows', []))} excluded source rows; {len(universe.get('unresolved_mappings', []))} unresolved equity mappings remain in coverage denominator.")
    icln = next((row for row in snapshot.get('themes', []) if row.get('anchor') == 'ICLN'), None)
    if icln:
        universe = raw.get('v5', {}).get('mapped_universes', {}).get('ICLN', {})
        lines += ['', '## ICLN score and breadth diagnostic', f"- Current {icln.get('current_strength_score')}; Medium {icln.get('medium_strength_score')}; Theme Score {icln.get('theme_score')}; state {icln.get('theme_state')}.", f"- EMA21 breadth: {icln.get('breadth_status_21')}; {icln.get('breadth_unavailable_reason_21') or 'valid'}.", f"- EMA50 breadth: {icln.get('breadth_status_50')}; {icln.get('breadth_unavailable_reason_50') or 'valid'}.", f"- Mapped holdings: {len(universe.get('companies', []))}; unresolved equity mappings: {len(universe.get('unresolved_mappings', []))}; official source rows: {universe.get('source_row_count')}."]
    lines += ['', '## Layer totals', f"- Eligible ETF anchors with no configured holdings parser (restored by removing holdings-parser eligibility gate): {restored}.", f"- ETF score failures: {score_failures}; only ETF/SPY return data and peer availability affect these.", f"- ETF breadth failures: {breadth_failures}; they do not affect ETF eligibility or score.", f"- Curated stock drilldown unavailable: {drilldown_unavailable}; it does not affect ETF eligibility or score."]
    diagnostics = snapshot.get('registry_diagnostics', [])
    active = sum(row.get('status') == 'selected_anchor' for row in diagnostics)
    themes = snapshot.get('themes', [])
    inactive = [row for row in diagnostics if row.get('status') != 'selected_anchor']
    by_reason = {}
    for row in inactive:
        reason = next((candidate.get('reasons', [None])[0] for candidate in row.get('candidates', []) if candidate.get('reasons')), 'No ETF candidate configured')
        by_reason[reason] = by_reason.get(reason, 0) + 1
    review_count = sum(len(row.get('candidates', [])) for row in diagnostics)
    completed_review_count = sum(candidate.get('mandate_review_complete', False) for row in diagnostics for candidate in row.get('candidates', []))
    reviewed_count = sum(candidate.get('mandate_review_status') == 'reviewed' for row in diagnostics for candidate in row.get('candidates', []))
    rejected_review_count = sum(candidate.get('mandate_review_status') == 'rejected' for row in diagnostics for candidate in row.get('candidates', []))
    adv_only = {
        candidate.get('ticker')
        for row in diagnostics for candidate in row.get('candidates', [])
        if candidate.get('status') == 'ineligible'
        and len(candidate.get('reasons', [])) == 1
        and 'average dollar volume' in candidate.get('reasons', [''])[0]
    }
    breadth_unavailable = sum(row.get('breadth_status_21') != 'valid' or row.get('breadth_status_50') != 'valid' for row in themes)
    drilldown = sum(bool(row.get('selected')) for row in themes)
    lines += ['', '## Registry coverage',
        f"- Registry records: {len(diagnostics)}; eligible published exposures: {active}; inactive exposures: {len(diagnostics)-active}.",
        '- Inactive exposures by first current eligibility reason: ' + (', '.join(f'{reason}: {count}' for reason, count in sorted(by_reason.items())) if by_reason else 'none') + '.',
        f"- ETF-only published exposures: {sum(not row.get('selected') for row in themes)}; published exposures with unavailable EMA21 or EMA50 breadth: {breadth_unavailable}.",
        f"- Published exposures with curated stock drilldowns: {drilldown}; without curated stock drilldowns: {len(themes)-drilldown}.",
        f"- Candidate mandate review outcomes: {completed_review_count}/{review_count} complete ({reviewed_count} compatible, {rejected_review_count} rejected); ETFs otherwise passing current checks but excluded by the ADV30 floor alone: {len(adv_only)} ({', '.join(sorted(adv_only)) or 'none'}).",
        f"- ETF mandate compatibility requires a dated issuer source and a candidate-specific rationale. The $10 million ADV30 floor is retained; it is a configurable screening convention, not a claim of universal suitability.",
        '', '## Registry audit', f"- Registry records: {len(diagnostics)}; runtime eligible anchors: {active}; inactive or unresolved this run: {len(diagnostics)-active}."]
    for row in diagnostics:
        lines.append(f"- {row.get('name')} ({row.get('id')}): {row.get('status')}; selected {row.get('selected_anchor') or 'none'}.")
        for candidate in row.get('candidates', []):
            reasons = '; '.join(candidate.get('reasons', [])) or 'passed configured runtime checks'
            lines.append(f"  - {candidate.get('ticker')}: {candidate.get('status')}; {reasons}")
            lines.append(f"    - Mandate review: {candidate.get('mandate_review_status')}; reviewed {candidate.get('mandate_review_date') or 'no review date'}; source filed {candidate.get('mandate_review_source_filed_date') or 'not applicable'}; {candidate.get('mandate_review_source') or 'no issuer source'}; {candidate.get('mandate_review_rationale') or 'no review rationale'}.")
            breadth_reasons = '; '.join(candidate.get('breadth_reasons', []))
            if breadth_reasons:
                lines.append(f"    - Breadth only: {breadth_reasons}")
    settings = snapshot.get('settings', {})
    scores = snapshot.get('score_methodology', {})
    lines += ['', '## Methodology and limits',
        f"- ETF candidates require at least {settings.get('anchor_minimum_history_sessions')} valid price sessions and ${settings.get('anchor_adv30_floor_usd', 0):,.0f} 30-session average dollar volume; AUM/spread are reported unavailable when a reproducible source is not configured.",
        '- CSV return fields use percentage values (`return5_pct`, `return21_pct`, `return63_pct`); excess returns and breadth changes use percentage points (`excess*_pp`, `breadth*_change_5_pp`).',
        '- Current and five-session-prior ranks use descending average ranks for exact score ties; rank change is t-5 rank minus current rank. Unavailable current scores sort last and have no numeric rank.',
        f"- Holdings breadth requires a dated official equity holdings source, at least {settings.get('minimum_breadth_sample')} valid companies, {settings.get('minimum_breadth_coverage', 0)*100:g}% price coverage, and holdings no older than {settings.get('maximum_holdings_age_days')} days. These checks do not enter scoring.",
        f"- Score weights are configured as {json.dumps(scores, sort_keys=True)}. This is a consistent relative-strength ranking for manual review, not a prediction or entry signal.",
        '- Missing score inputs are not imputed or reweighted. ETF and index breadth use complete sourced equity universes independently of curated stock watchlists.',
        '- Index and ETF memberships are current source snapshots, not historical point-in-time universes. Yahoo adjusted-close semantics are vendor conventions.',
        '- Nasdaq market-cap fields have no separate observation timestamps, so stock eligibility remains provisional. Sector stock watchlists use current S&P 500 classifications intersected with official sector ETF holdings and the configured price, cap and liquidity filters.',
        '- Ineligible anchors, unavailable ETF scores, unavailable breadth, and missing curated stock drilldowns are separate statuses. Missing breadth or stocks does not make an ETF ineligible.',
        '', '## Source errors', '```json', json.dumps({'core': raw.get('errors', {}), 'constituent_histories':raw.get('v5', {}).get('chart_errors', {})}, indent=2), '```',
        '', '## Sector stock-list scope', 'Sector stock candidates are the current S&P 500 sector classification intersected with official selected-sector ETF holdings, then filtered by the configured listed-equity, price, market-cap and ADV rules. This is not every listed company in each sector. Per-company evidence and exclusions are in stock_diagnostics.csv.',
        '', '## Local files', 'dashboard.html, market.csv, themes.csv, registry_audit.csv, stock_diagnostics.csv, latest_snapshot.json, raw_inputs.json, iwm_breadth_prices.csv.gz, Inter-LICENSE.txt, source_matrix.csv, watchlist_15.csv, watchlist_20.csv, tradingview_15.txt, tradingview_20.txt, run_bundle.zip.', 'Generated runs are ignored under dist/ or output/. Refresh with python scripts/generate_dashboard.py. Failed refreshes preserve existing valid exports and write refresh_status.json/failed_refresh.md separately.']
    return '\n'.join(lines)+'\n'


RUN_OUTPUT_FILES = (
    "market.csv", "themes.csv", "registry_audit.csv", "stock_diagnostics.csv", "membership_review.csv",
    "theme_watchlist_summary.csv", "release_audit.json",
    "dashboard.html",
    "latest_snapshot.json",
    "raw_inputs.json",
    "iwm_breadth_prices.csv.gz",
    "market_breadth_prices.csv.gz",
    "watchlist_prices.csv.gz",
    "Inter-LICENSE.txt",
    "source_matrix.csv",
    "watchlist_20.csv",
    "tradingview_20.txt",
    "individual_theme_exports.json", "individual_theme_txt.zip",
    "latest_run.md",
    "watchlist_migration.md",
    "theme_watchlists.json",
    "active_anchors.json",
    "methodology_config.json",
)


def _write_run_bundle(output_dir: Path, maximum_bytes: int = 95_000_000) -> Path:
    bundle_path = output_dir / "run_bundle.zip"
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for filename in RUN_OUTPUT_FILES:
            source = output_dir / filename
            if not source.is_file():
                raise FileNotFoundError(f"Missing run output required for bundle: {source}")
            bundle.write(source, arcname=filename)
    size = bundle_path.stat().st_size
    if size > maximum_bytes:
        bundle_path.unlink(missing_ok=True)
        raise ValueError(f"run_bundle.zip is {size:,} bytes; configured limit is {maximum_bytes:,}. Reduce retained run inputs or raise settings.maximum_run_bundle_bytes deliberately.")
    return bundle_path


def _generate(snapshot, raw, output_dir):
    release_audit = audit_release(ROOT, snapshot_data=snapshot)
    if not release_audit.get('passed'):
        failures = '; '.join(issue['message'] for issue in release_audit.get('issues', [])[:8])
        raise ValueError(f"Release audit failed; no bundle generated. {failures}")
    if snapshot.get("methodology_version") == "approved-1":
        from scripts.audit_approved import audit as approved_audit
        approved_result = approved_audit(ROOT)
        release_audit = {**release_audit, "approved_release": approved_result, "passed": approved_result["passed"] and snapshot.get("data_complete", False), "run_kind": snapshot.get("run_kind")}
    matrix = make_source_matrix(snapshot, raw, ROOT)
    snapshot["source_matrix"] = matrix
    output_dir.mkdir(parents=True, exist_ok=True)
    v5_charts = raw.get('v5', {}).get('charts', {})
    iwm_charts = raw.get("v5", {}).get("iwm_breadth_charts", {})
    iwm_symbols = set(iwm_charts)
    watch_symbols = {stock.get('ticker') for theme in snapshot.get('themes', []) for stock in theme.get('selected', [])}
    watch_charts = {key: value for key, value in v5_charts.items() if key in watch_symbols and key not in iwm_symbols}
    market_charts = {key: value for key, value in v5_charts.items() if key not in watch_symbols and key not in iwm_symbols}
    # Preserve any configured stock history that also belongs to the IWM proxy
    # in the broad sidecar; apply_watchlists merges all three chart groups.
    _write_iwm_sidecar(output_dir / "iwm_breadth_prices.csv.gz", iwm_charts)
    _write_chart_sidecar(output_dir / 'market_breadth_prices.csv.gz', market_charts)
    _write_chart_sidecar(output_dir / 'watchlist_prices.csv.gz', watch_charts)
    settings = snapshot.get('settings', {})
    _write_json(output_dir / "latest_snapshot.json", _primary_snapshot(snapshot))
    raw_output = _compact_raw(raw, snapshot, {'market': len(market_charts), 'watchlist': len(watch_charts), 'iwm': len(iwm_charts)})
    _write_bounded_json(output_dir / "raw_inputs.json", raw_output, int(settings.get('maximum_raw_inputs_bytes', 99_000_000)), 'raw_inputs.json')
    shutil.copyfile(ROOT / "static/Inter-LICENSE.txt", output_dir / "Inter-LICENSE.txt")
    shutil.copyfile(ROOT / 'config/theme_watchlists.json', output_dir / 'theme_watchlists.json')
    shutil.copyfile(ROOT / 'config/active_anchors.json', output_dir / 'active_anchors.json')
    _write_json(output_dir / 'methodology_config.json', {'methodology_version': '7.1', 'settings': settings, 'score_methodology': snapshot.get('score_methodology', {}), 'active_anchor_source_session': json.loads((ROOT / 'config/active_anchors.json').read_text()).get('source_session')})
    _write_json(output_dir / 'release_audit.json', release_audit)
    _write_csv(output_dir / "source_matrix.csv", matrix, list(matrix[0].keys()) if matrix else [])

    theme_records = sorted(snapshot.get('themes', []), key=lambda row: (
        row.get('global_rank') is None,
        row.get('global_rank') if row.get('global_rank') is not None else float('inf'),
        str(row.get('id', '')),
    ))
    market_records = list(snapshot.get('context', [])) + list(snapshot.get('volatility_context', []))
    for filename, records in [('market.csv', market_records), ('themes.csv', theme_records)]:
        flat = []
        for record in records:
            row = _theme_csv_row(record) if filename == 'themes.csv' else _market_csv_row(record, snapshot['session_date'], snapshot.get('dashboard_generated_at') or snapshot['generated_at'])
            row['session_date'] = snapshot['session_date']
            row['generated_at'] = snapshot.get('dashboard_generated_at') or snapshot['generated_at']
            if record.get('instrument_type') == 'volatility_index':
                row['instrument_type'] = 'volatility_index'
                row.pop('index_breadth', None)
                row.pop('holdings_breadth', None)
            elif filename == 'market.csv':
                for period in (21, 50):
                    breadth = record.get('index_breadth', {}).get(str(period), {})
                    row[f'index_breadth{period}_pct'] = breadth.get('value')
                    row[f'index_breadth{period}_above_count'] = breadth.get('above_count')
                    row[f'index_breadth{period}_valid_count'] = breadth.get('valid_count')
                    row[f'index_breadth{period}_eligible_count'] = breadth.get('eligible_count')
                    row[f'breadth{period}_t_minus_5'] = record.get(f'breadth{period}_t_minus_5')
                    row[f'breadth{period}_change_5_pp'] = record.get(f'breadth{period}_change_5_pp')
            flat.append(row)
        columns = THEME_EXPORT_COLUMNS if filename == 'themes.csv' else MARKET_EXPORT_COLUMNS
        _write_csv(output_dir / filename, flat, columns)
    registry_rows = []
    for exposure in snapshot.get('registry_diagnostics', []):
        candidates = exposure.get('candidates', [])
        if raw.get('v7_mode') and not candidates:
            candidates = [{'ticker': None, 'status': 'not_collected', 'reasons': [exposure.get('inactive_reason') or 'Inactive registry record retained from the prior eligibility review.']}]
        for candidate in candidates:
            if raw.get('v7_mode'):
                registry_rows.append({
                    'id': exposure.get('id'), 'name': exposure.get('name'), 'type': exposure.get('type'),
                    'status': exposure.get('status'), 'selected_anchor': exposure.get('selected_anchor'),
                    'candidate_ticker': candidate.get('ticker'), 'candidate_status': candidate.get('status'),
                    'candidate_reasons': '; '.join(candidate.get('reasons', [])),
                    'instrument_type': candidate.get('instrument_type'), 'currency': candidate.get('currency'),
                    'valid_history_sessions': candidate.get('valid_history_sessions'),
                    'adv30_usd': candidate.get('adv30_usd'), 'minimum_adv30_usd': candidate.get('minimum_adv30_usd'),
                    'inactive_reason': exposure.get('inactive_reason'),
                })
                continue
            registry_rows.append({
                'id': exposure.get('id'), 'name': exposure.get('name'), 'type': exposure.get('type'),
                'charter_status': exposure.get('charter_status'), 'charter': exposure.get('charter'),
                'status': exposure.get('status'), 'selected_anchor': exposure.get('selected_anchor'),
                'selected_anchor_reason': exposure.get('selected_anchor_reason'), 'candidate_ticker': candidate.get('ticker'),
                'candidate_priority': candidate.get('candidate_priority'), 'candidate_status': candidate.get('status'),
                'candidate_reasons': '; '.join(candidate.get('reasons', [])), 'fund_name': candidate.get('fund_name'),
                'mandate_review_status': candidate.get('mandate_review_status'),
                'mandate_review_date': candidate.get('mandate_review_date'),
                'mandate_review_source': candidate.get('mandate_review_source'),
                'mandate_review_source_filed_date': candidate.get('mandate_review_source_filed_date'),
                'mandate_review_rationale': candidate.get('mandate_review_rationale'),
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
    stock_columns = list(stock_rows[0]) if stock_rows else ['theme_id','theme','type','anchor','ticker','company','eligibility','eligibility_reasons','return5_pct','return21_pct','return63_pct','excess5_pp','excess21_pp','excess63_pp','session_date']
    _write_csv(output_dir / 'stock_diagnostics.csv', stock_rows, stock_columns)
    membership_rows = _membership_review_rows(raw.get('watchlists') or {}, snapshot.get('themes', []))
    membership_columns = list(membership_rows[0]) if membership_rows else [
        'theme_id','theme','anchor','status','reviewed_candidate_count','exception_reason','list_rationale',
        'ticker','company','exchange','instrument_type','relationship','reason','maintenance_date',
        'candidate_source','price_usd','market_cap_usd','adv30_usd','adjusted_price_sessions',
        'history_source','history_as_of','source_url','reason_source_url',
    ]
    _write_csv(output_dir / 'membership_review.csv', membership_rows, membership_columns)
    theme_summary_rows = _theme_watchlist_summary(snapshot)
    _write_csv(output_dir / 'theme_watchlist_summary.csv', theme_summary_rows, list(theme_summary_rows[0]) if theme_summary_rows else ['theme_id','name','anchor','status','member_count'])
    rows15 = _all_selected(snapshot, 20)
    rows20 = _all_selected(snapshot, 20)
    individual = {}
    for theme in snapshot.get("themes", []):
        content, diagnostics = _tradingview_text(_all_selected({"themes": [theme]}, 20))
        individual[theme["id"]] = {"symbols": content, "diagnostics": diagnostics}
    _write_json(output_dir / "individual_theme_exports.json", individual)
    with zipfile.ZipFile(output_dir / "individual_theme_txt.zip", "w", compression=zipfile.ZIP_DEFLATED) as theme_zip:
        for theme_id, item in individual.items():
            theme_zip.writestr(theme_id + ".txt", item["symbols"])
    _write_csv(output_dir / "watchlist_20.csv", rows20, EXPORT_COLUMNS)
    text15, stats15 = _tradingview_text(rows15)
    text20, stats20 = _tradingview_text(rows20)
    (output_dir / "tradingview_20.txt").write_text(text20, encoding="utf-8")
    report = _v7_run_report(snapshot, raw) if raw.get('v7_mode') else _run_report(snapshot, raw, matrix, stats15, stats20)
    if snapshot.get("run_kind") == "offline_historical_diagnostic":
        report = "# Historical offline diagnostic\n\nNot a live refresh or a data-complete approved release. Retained historical prices were recalculated under the approved rules. Target-20 membership review and source access/rights remain separate gates.\n\nSession: " + str(snapshot.get("session_date")) + "\n"
    (output_dir / "latest_run.md").write_text(report, encoding="utf-8")
    migration = report if snapshot.get('run_kind') == 'offline_historical_diagnostic' else _watchlist_migration_report(snapshot, raw) if raw.get('v7_mode') else '# ThemeScope v7 watchlist migration\n\nThe current output was generated before the v7 migration.\n'
    (output_dir / 'watchlist_migration.md').write_text(migration, encoding='utf-8')

    template = (ROOT / "static/dashboard_template.html").read_text(encoding="utf-8")
    style = (ROOT / "static/dashboard.css").read_text(encoding="utf-8")
    script = (ROOT / "static/dashboard.js").read_text(encoding="utf-8")
    ui_snapshot = _dashboard_snapshot(snapshot)
    payload = json.dumps(ui_snapshot, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    font_data = base64.b64encode((ROOT / "static/InterVariable.woff2").read_bytes()).decode("ascii")
    html = template.replace("{{STYLE}}", style.replace("{{FONT_DATA}}", font_data)).replace("{{SCRIPT}}", script).replace("{{SNAPSHOT_JSON}}", payload)
    if "{{STYLE}}" in html or "{{SCRIPT}}" in html or "{{SNAPSHOT_JSON}}" in html or "{{FONT_DATA}}" in html:
        raise RuntimeError("Dashboard template placeholder replacement failed")
    if snapshot.get("run_kind") == "offline_historical_diagnostic":
        html = html.replace('href="run_bundle.zip"', 'href="diagnostic_bundle.zip"').replace("Download complete run ZIP", "Download historical diagnostic ZIP")
    html_size = len(html.encode('utf-8'))
    max_dashboard_bytes = int(settings.get('maximum_dashboard_bytes', 20_000_000))
    if html_size > max_dashboard_bytes:
        raise ValueError(f"dashboard.html is {html_size:,} bytes; configured limit is {max_dashboard_bytes:,}. Remove UI-irrelevant data or raise settings.maximum_dashboard_bytes deliberately.")
    (output_dir / "dashboard.html").write_text(html, encoding="utf-8")
    bundle_path = _write_run_bundle(output_dir, int(settings.get('maximum_run_bundle_bytes', 95_000_000)))
    if snapshot.get("run_kind") == "offline_historical_diagnostic":
        renamed = output_dir / "diagnostic_bundle.zip"
        os.replace(bundle_path, renamed)
        bundle_path = renamed

    return bundle_path


def load_approved_config():
    path = ROOT / "config/approved_release.json"
    return json.loads(path.read_text()) if path.exists() else {}




def _manual_csv_outputs(snapshot: dict[str, Any], raw: dict[str, Any], output_dir: Path) -> None:
    """Write the compact local-only manual CSV release without live-source artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    from src.themescope.daily_lists import build as build_daily_lists
    from src.themescope.research_policy import ema_relationship
    export_files = build_daily_lists(snapshot, snapshot["export_configuration"])
    for name, content in export_files.items():
        (output_dir / name).parent.mkdir(parents=True, exist_ok=True)
        (output_dir / name).write_text(content, encoding="utf-8", newline="\n")
    audit = snapshot["manual_csv_audit"]
    _write_json(output_dir / "latest_snapshot.json", snapshot)
    _write_json(output_dir / "run_audit.json", audit)
    _write_json(output_dir / "canonical_dashboard_data.json", {
        "session_date": snapshot["session_date"],
        "market_classification": snapshot["market_classification"],
        "context": snapshot["context"],
        "themes": snapshot["themes"],
        "expected_earnings": snapshot["expected_earnings"],
        "export_manifest": snapshot["export_manifest"],
        "decision": snapshot["decision"], "daily_primary_research": snapshot["daily_primary_research"],
    })
    market_rows = []
    for row in snapshot["context"]:
        metric21, metric50 = row["index_breadth"]["21"], row["index_breadth"]["50"]
        market_rows.append({
            "ticker": row["ticker"], "price": row["price_close"], "ema21": row["ema21"], "ema50": row["ema50"],
            "price_state": row["price_state"], "breadth21_pct": metric21["value"], "breadth50_pct": metric50["value"],
            "breadth_state": row["breadth_state"], "valid_rows": metric21["valid_count"], "denominator": metric21["eligible_count"],
            "session_date": snapshot["session_date"],
        })
    _write_csv(output_dir / "market.csv", market_rows, list(market_rows[0]))
    theme_rows = []
    stock_rows = []
    for row in sorted(snapshot["themes"], key=lambda item: (item.get("global_rank") is None, item.get("global_rank") or 10**9)):
        theme_rows.append({
            "rank": row.get("global_rank"), "type": row.get("level"), "theme_id": row["id"], "name": row["name"], "anchor": row["anchor"],
            "change_1d_pct": row["daily_change"] * 100 if row.get("daily_change") is not None else None,
            "rank_change_daily": row.get("rank_change_daily"), "rank_comparison_session": row.get("rank_comparison_session"),
            "vs_ema21": ema_relationship(row.get("price_close"),row.get("ema21")), "vs_ema50": ema_relationship(row.get("price_close"),row.get("ema50")),
            "priority_change": row.get("priority_change"), "research_priority": row.get("research_priority", {}).get("label"), "theme_score": row.get("theme_score"),
            "current": row.get("current_strength_score"), "medium": row.get("medium_strength_score"),
            "performance_1w_pct": row.get("returns", {}).get("5", {}).get("value") * 100 if row.get("returns", {}).get("5", {}).get("value") is not None else None,
            "performance_1m_pct": row.get("returns", {}).get("21", {}).get("value") * 100 if row.get("returns", {}).get("21", {}).get("value") is not None else None,
            "performance_3m_pct": row.get("returns", {}).get("63", {}).get("value") * 100 if row.get("returns", {}).get("63", {}).get("value") is not None else None,
            "price": row.get("price_close"), "ema21": row.get("ema21"), "ema50": row.get("ema50"),
            "theme_breadth21_pct": row.get("theme_breadth21_pct"), "theme_breadth50_pct": row.get("theme_breadth50_pct"),
            "configured_stock_count": row.get("configured_watchlist_count"), "session_date": snapshot["session_date"],
        })
        for stock in row.get("selected", []):
            stock_rows.append({
                "theme_id": row["id"], "theme": row["name"], "anchor": row["anchor"], "ticker": stock["ticker"], "company": stock.get("company"),
                "exchange": stock.get("exchange"), "relationship": stock.get("membership_tag"), "membership_reason": stock.get("membership_rationale"),
                "market_cap_usd": stock.get("market_cap_usd"), "excess_1m_pp": stock.get("excess21_pp"), "excess_3m_pp": stock.get("excess63_pp"),
                "metric_status": stock.get("metric_status"), "price": stock.get("price_close"), "change_1d_pct": stock.get("daily_change") * 100 if stock.get("daily_change") is not None else None,
                "performance_1w_pct": stock.get("returns", {}).get("5", {}).get("value") * 100 if stock.get("returns", {}).get("5", {}).get("value") is not None else None,
                "performance_1m_pct": stock.get("returns", {}).get("21", {}).get("value") * 100 if stock.get("returns", {}).get("21", {}).get("value") is not None else None,
                "performance_3m_pct": stock.get("returns", {}).get("63", {}).get("value") * 100 if stock.get("returns", {}).get("63", {}).get("value") is not None else None,
                "ema21": stock.get("ema21"), "ema50": stock.get("ema50"), "atr14_pct": stock.get("atr14_pct"), "adv30_usd": stock.get("adv30_usd"),
                "turnover_1d_usd": stock.get("turnover_1d_usd"), "relative_volume_1d": stock.get("relative_volume_1d"), "sector": stock.get("sector"),
                "industry": stock.get("industry"), "upcoming_earnings_date": stock.get("earnings_date"), "session_date": snapshot["session_date"],
            })
    _write_csv(output_dir / "themes.csv", theme_rows, list(theme_rows[0]))
    _write_csv(output_dir / "theme_stocks.csv", stock_rows, list(stock_rows[0]) if stock_rows else ["theme_id", "ticker", "metric_status"])

    etf_lines = list(dict.fromkeys(row["tradingview_symbol"] for row in snapshot["themes"] + snapshot["context"]))
    (output_dir / "tradingview_sector_theme_etfs.txt").write_text(",".join(etf_lines) + "\n", encoding="utf-8")
    individual = {}
    with zipfile.ZipFile(output_dir / "individual_theme_watchlists.zip", "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for item in snapshot['export_manifest']:
            if item['role'] != 'individual_research':continue
            content=export_files[item['file']]
            individual[item['theme_id']]={**item,'symbols':content.strip().split(',')}
            bundle.writestr(Path(item['file']).name,content)
    _write_json(output_dir / "individual_theme_watchlists.json", individual)
    research=snapshot['daily_primary_research']
    if research['archive_file']:
        with zipfile.ZipFile(output_dir/research['archive_file'],'w',compression=zipfile.ZIP_DEFLATED) as bundle:
            for item in snapshot['export_manifest']:
                if item['role']=='individual_primary_research':bundle.writestr(Path(item['file']).name,export_files[item['file']])
        relationships=research['relationships']
        _write_csv(output_dir/research['relationships_file'],relationships,list(relationships[0]))
    _write_json(output_dir/'daily_primary_audit.json',research)

    audit["tradingview"] = {"identifier_evidence": "config/tradingview_symbols.json", "platform_import_tested": False,
        "grouped_duplicate_behavior": "User-confirmed round-trip observation: repeated symbols retained once; raw round-trip files unavailable in this session",
        "broad_scan_sections": False, "individual_section_headings": False, "anchor_first": True, "unresolved": []}

    template = (ROOT / "static/dashboard_template.html").read_text(encoding="utf-8")
    style = (ROOT / "static/dashboard.css").read_text(encoding="utf-8")
    script = (ROOT / "static/dashboard.js").read_text(encoding="utf-8")
    template = template.replace('href="registry_audit.csv"', 'href="run_audit.json"').replace("Registry audit CSV", "Run audit JSON").replace('href="stock_diagnostics.csv"', 'href="theme_stocks.csv"').replace("Stock eligibility audit", "Configured stock CSV")
    payload = json.dumps(_dashboard_snapshot(snapshot), ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    font_data = base64.b64encode((ROOT / "static/InterVariable.woff2").read_bytes()).decode("ascii")
    html = template.replace("{{STYLE}}", style.replace("{{FONT_DATA}}", font_data)).replace("{{SCRIPT}}", script).replace("{{SNAPSHOT_JSON}}", payload)
    if re.search(r"<(?:script|link|img)[^>]+(?:src|href)=[\"']https?://", html, re.I):
        raise ValueError("Generated dashboard contains an automatic external resource request")
    if "connect-src 'none'" not in html:
        raise ValueError("Generated dashboard does not block automatic network connections")
    (output_dir / "dashboard.html").write_text(html, encoding="utf-8")
    shutil.copyfile(ROOT / "static/Inter-LICENSE.txt", output_dir / "Inter-LICENSE.txt")
    _write_json(output_dir / "refresh_status.json", {"status": "success", "source": "tradingview-csv", "data_date": snapshot["session_date"], "data_complete": True})
    (output_dir / "latest_run.md").write_text(
        "# Manual CSV run\n\nUS session: " + snapshot["session_date"] + "\n\nMarket: " + snapshot["decision"]["market_classification"] +
        "\n\n" + snapshot["decision"]["reason"] + "\n\nDetailed metrics and input hashes: run_audit.json. TradingView platform import has not been performed.\n", encoding="utf-8")
    audit["export_file_counts"] = {"theme_watchlists": len(individual), "canonical_json": 1, "csv": 3 + bool(research["relationships_file"]), "tradingview_text": len(snapshot["export_manifest"]), "watchlist_zip": len(snapshot["export_archives"])}
    audit["browser_validation"] = {"inline_assets": True, "csp_connect_none": True, "automatic_external_requests": "not measured by generator; see browser audit"}
    audit["publication_pass"] = True
    _write_json(output_dir / "run_audit.json", audit)


def _run_manual_csv_unlocked(args: argparse.Namespace, output: Path, launched_at: float) -> int:
    from src.themescope.manual_csv import build_release
    from src.themescope.local_history import apply as apply_history
    paths = {role: getattr(args, role + "_csv") for role in ("stock", "etf", "spy", "qqq", "iwm")}
    attempted = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        build_started = time.perf_counter()
        snapshot, raw = build_release(ROOT, paths, args.as_of)
        history_record = apply_history(snapshot, output / "local_history", ROOT / "config/calendars/xnys_2020_2035_v1.json")
        # An older rerun may replace the displayed dashboard, but it must not
        # rewrite evidence already used by later-session comparisons.
        later=list((output/'local_history').glob('????-??-??.json'))
        if any(path.stem>snapshot['session_date'] for path in later):
            original=output/'local_history'/(snapshot['session_date']+'.json')
            if not original.exists() or json.loads(original.read_text(encoding='utf-8'))!=history_record:
                raise ValueError('Older-session rerun would change history used by a later session. Original history was preserved. Use the original inputs/configuration or a separate output folder for alternate historical calculations.')
        build_elapsed = time.perf_counter() - build_started
        previous_exports = {"tradingview_all_theme_stocks.txt"}
        previous_path = output / "latest_snapshot.json"
        if previous_path.exists():
            try:
                previous_snapshot = json.loads(previous_path.read_text(encoding='utf-8'))
                previous_exports.update(item["file"] for item in previous_snapshot.get("export_manifest", []))
                previous_exports.update(previous_snapshot.get("export_archives", []))
                relationship_file=previous_snapshot.get('daily_primary_research',{}).get('relationships_file')
                if relationship_file:previous_exports.add(relationship_file)
            except (ValueError, KeyError, TypeError, AttributeError):
                pass  # Unknown artifacts are preserved, never guessed for deletion.
        # Retire only generated export namespaces, never inputs, audit/history
        # records or arbitrary files. This also cleans old dated Primary lists.
        for pattern in ('tradingview_daily_primary_*.txt','daily_primary_watchlists_*.zip','daily_primary_relationships_*.csv','primary_watchlists/*/*.txt','individual_watchlists/*.txt'):
            previous_exports.update(path.relative_to(output).as_posix() for path in output.glob(pattern))
        managed=re.compile(r'(?:tradingview_[A-Za-z0-9_-]+\.(?:txt|zip)|daily_primary_(?:watchlists_\d{4}-\d{2}-\d{2}\.zip|relationships_\d{4}-\d{2}-\d{2}\.csv)|(?:individual_watchlists|primary_watchlists/\d{4}-\d{2}-\d{2})/[A-Za-z0-9_.-]+\.txt)')
        current_exports={item['file'] for item in snapshot['export_manifest']}|set(snapshot['export_archives'])
        if snapshot.get('daily_primary_research',{}).get('relationships_file'):current_exports.add(snapshot['daily_primary_research']['relationships_file'])
        obsolete_exports={name for name in previous_exports if isinstance(name,str) and managed.fullmatch(name)}-current_exports

        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".themescope-manual-stage-", dir=output.parent) as temporary:
            stage = Path(temporary) / "run"
            _manual_csv_outputs(snapshot, raw, stage)
            elapsed = time.perf_counter() - launched_at
            snapshot["manual_csv_audit"]["runtime_seconds"] = elapsed
            snapshot["manual_csv_audit"]["runtime_stages"] = {
                "input_validation_and_calculation": build_elapsed,
                "output_generation_and_validation": max(0.0, elapsed - build_elapsed),
                "total_from_command_start_through_validation": elapsed,
            }
            _write_json(stage / "latest_snapshot.json", snapshot)
            _write_json(stage / "run_audit.json", snapshot["manual_csv_audit"])
            # Re-embed the final audit/runtime values before publication.
            template = (ROOT / "static/dashboard_template.html").read_text(encoding="utf-8")
            style = (ROOT / "static/dashboard.css").read_text(encoding="utf-8")
            script = (ROOT / "static/dashboard.js").read_text(encoding="utf-8")
            template = template.replace('href="registry_audit.csv"', 'href="run_audit.json"').replace("Registry audit CSV", "Run audit JSON").replace('href="stock_diagnostics.csv"', 'href="theme_stocks.csv"').replace("Stock eligibility audit", "Configured stock CSV")
            payload = json.dumps(_dashboard_snapshot(snapshot), ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
            font_data = base64.b64encode((ROOT / "static/InterVariable.woff2").read_bytes()).decode("ascii")
            (stage / "dashboard.html").write_text(template.replace("{{STYLE}}", style.replace("{{FONT_DATA}}", font_data)).replace("{{SCRIPT}}", script).replace("{{SNAPSHOT_JSON}}", payload), encoding="utf-8")
            existing_history=output / "local_history" / (snapshot["session_date"] + ".json")
            if existing_history.is_file():
                previous_bytes=existing_history.read_bytes()
                previous_record=json.loads(previous_bytes)
                if previous_record.get('research_history',{}).get('priority_methodology') != history_record.get('research_history',{}).get('priority_methodology'):
                    import hashlib
                    saved=stage / 'local_history' / 'backups' / (snapshot['session_date']+'.pre-priority-migration.'+hashlib.sha256(previous_bytes).hexdigest()[:12]+'.json')
                    saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(previous_bytes)
            _write_json(stage / "local_history" / (snapshot["session_date"] + ".json"), history_record)
            bundle_files = [path for path in stage.rglob("*") if path.is_file() and path.name != "run_bundle.zip"]
            with zipfile.ZipFile(stage / "run_bundle.zip", "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                for path in bundle_files:
                    bundle.write(path, arcname=str(path.relative_to(stage)))
            import hashlib,uuid
            publication_files={path.relative_to(stage).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in stage.rglob('*') if path.is_file() and not path.relative_to(stage).parts[0]=='local_history'}
            _write_json(stage/'publication_manifest.json',{'schema':'themescope-local-publication-1','session_date':snapshot['session_date'],'publication_id':uuid.uuid4().hex,'files':publication_files})
            from src.themescope.local_publication import publish_tree
            publish_tree(stage,output,obsolete_exports)
        (output / "failed_attempt_audit.json").unlink(missing_ok=True)
        print(f"SUCCESS: manual CSV session {snapshot['session_date']}; {len(snapshot['themes'])} anchors; completed in {time.perf_counter()-launched_at:.3f}s")
        print(f"Open {output / 'dashboard.html'}\nAudit: {output / 'run_audit.json'}\nDownload bundle: {output / 'run_bundle.zip'}")
        return 0
    except Exception as exc:
        output.mkdir(parents=True, exist_ok=True)
        preserved_date = None
        from src.themescope.local_publication import pending
        if not pending(output) and (output / "latest_snapshot.json").is_file() and (output / "dashboard.html").is_file():
            try:
                preserved_date = json.loads((output / "latest_snapshot.json").read_text(encoding="utf-8")).get("session_date")
            except (OSError, ValueError):
                preserved_date = None
        _write_json(output / "failed_attempt_audit.json", {"status": "failed", "source": "tradingview-csv", "attempted_at": attempted, "declared_us_session": args.as_of, "reason": f"{type(exc).__name__}: {exc}", "dashboard_preserved": bool(preserved_date), "preserved_data_date": preserved_date, "runtime_seconds": time.perf_counter() - launched_at})
        print(f"MANUAL CSV GENERATION FAILED: {exc}\n" + (f"Existing dashboard preserved with session {preserved_date}." if preserved_date else "No successful dashboard exists in this output directory.") + f"\nDetails: {output / 'failed_attempt_audit.json'}", file=sys.stderr)
        return 1


def _run_manual_csv(args,output,launched_at):
    from src.themescope.local_publication import output_lock,recover
    try:
        with output_lock(output,timeout=5):
            recover(output)
            return _run_manual_csv_unlocked(args,output,launched_at)
    except (OSError,ValueError) as error:
        print('MANUAL CSV GENERATION FAILED: '+str(error)+'; no new successful run was published.',file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    launched_at = time.perf_counter()
    entered_collection = False
    parser = argparse.ArgumentParser(description="Collect live ThemeScope data after approved-source preflight, or import a dated run offline.")
    parser.add_argument('--output-dir', default='output')
    parser.add_argument('--source', choices=('live', 'tradingview-csv'), default='live')
    parser.add_argument('--import-run', type=Path, help='Import a dated real run directory or run_bundle.zip; no network requests')
    parser.add_argument('--as-of', help='Resolve the latest verified completed common US session on or before YYYY-MM-DD')
    for role in ('stock', 'etf', 'spy', 'qqq', 'iwm'):
        parser.add_argument(f'--{role}-csv', type=Path, help=f'Explicit {role.upper()} CSV input for --source tradingview-csv')
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
    if args.source == 'tradingview-csv':
        if args.import_run:
            parser.error('--import-run cannot be combined with --source tradingview-csv')
        if not args.as_of:
            parser.error('--as-of is required for --source tradingview-csv')
        missing_roles = [role for role in ('stock', 'etf', 'spy', 'qqq', 'iwm') if getattr(args, role + '_csv') is None]
        if missing_roles:
            parser.error('manual CSV mode requires: ' + ', '.join('--' + role + '-csv' for role in missing_roles))
        return _run_manual_csv(args, output, launched_at)
    approved_config = load_approved_config()
    if approved_config.get("enabled") and args.import_run and (output/"dashboard.html").exists():
        try:
            previous = json.loads((output/"latest_snapshot.json").read_text())
        except (OSError, ValueError):
            previous = {}
        if previous.get("run_kind") != "offline_historical_diagnostic":
            output = output/"approved_diagnostic"
    if approved_config.get("enabled") and not args.import_run:
        from src.themescope.approved_data import preflight
        from scripts.audit_approved import audit as audit_approved
        gate = preflight(ROOT)
        configuration_gate = audit_approved(ROOT)
        gate["issues"].extend(configuration_gate["configuration_issues"])
        gate["issues"].extend(configuration_gate.get("export_issues", []))
        gate["passed"] = not gate["issues"]
        output.mkdir(parents=True, exist_ok=True)
        _write_json(output / "attempt_preflight.json", gate)
        if not gate["passed"]:
            from src.themescope.approved_data import record_attempt
            record_attempt(ROOT / "cache/approved_attempts.jsonl", kind="live", entered_collection=False, target=args.as_of, data_complete=False, publication_pass=False, elapsed=time.perf_counter()-launched_at, detail=gate["issues"])
            print("LIVE PREFLIGHT BLOCKED: " + "; ".join(gate["issues"]), file=sys.stderr)
            return 1

    config_audit = audit_release(ROOT)
    if not config_audit.get('passed'):
        messages = '; '.join(issue['message'] for issue in config_audit.get('issues', [])[:8])
        print(f"RELEASE BLOCKED before collection: watchlist configuration audit failed. {messages}", file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    snapshot, raw, imported_context = {}, {}, []
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
                    if 'iwm_breadth_prices.csv.gz' in bundle.namelist():
                        _load_iwm_sidecar(raw, bundle.read('iwm_breadth_prices.csv.gz'))
                    for name in ('market_breadth_prices.csv.gz', 'watchlist_prices.csv.gz'):
                        if name in bundle.namelist():
                            _load_chart_sidecar(raw, bundle.read(name), name)
            else:
                snapshot = json.loads((args.import_run / 'latest_snapshot.json').read_text(encoding='utf-8'))
                raw = json.loads((args.import_run / 'raw_inputs.json').read_text(encoding='utf-8'))
                sidecar = args.import_run / 'iwm_breadth_prices.csv.gz'
                if sidecar.is_file():
                    _load_iwm_sidecar(raw, sidecar.read_bytes())
                for name in ('market_breadth_prices.csv.gz', 'watchlist_prices.csv.gz'):
                    path = args.import_run / name
                    if path.is_file():
                        _load_chart_sidecar(raw, path.read_bytes(), name)
            if not snapshot.get('generated_at') or not snapshot.get('session_date'):
                raise ValueError('Imported run must retain its original generation time and session date')
            imported_context = copy.deepcopy(snapshot.get('context', []))
            if args.as_of and args.as_of != snapshot.get('session_date'):
                raise ValueError('This imported bundle contains one resolved date only; use a fresh collection to resolve --as-of.')
            snapshot['imported_at'] = attempted
            raw['v7_mode'] = True
            retained = len(raw.get('charts', {})) + len(raw.get('v5', {}).get('charts', {})) + len(raw.get('v5', {}).get('iwm_breadth_charts', {}))
            raw['price_cache_stats'] = {'hits': retained, 'requests': 0, 'incremental_updates': 0, 'full_refreshes': 0, 'failures': 0, 'stale_reuses': 0, 'offline_import_histories_reused': retained}
            raw['collection_request_counts'] = {'price_history': 0, 'universe': 0, 'filings': 0, 'quotes': 0, 'theme_holdings': 0, 'aum_spread': 0}
        else:
            print('Collecting required market, anchor, index and configured-watchlist prices. Please wait.', flush=True)
            if approved_config.get("enabled"):
                from src.themescope.collect_approved import build_snapshot as collect_approved
                entered_collection = True
                snapshot, raw = collect_approved(ROOT, args.as_of)
            else:
                snapshot, raw = build_snapshot(ROOT, args.as_of)
        if args.as_of:
            snapshot['requested_asof'] = args.as_of
        registry = json.loads((ROOT / 'config/themes.json').read_text(encoding='utf-8'))
        active_config = json.loads((ROOT / 'config/active_anchors.json').read_text(encoding='utf-8'))
        registry = raw.get('v7_registry') or _restricted_registry(registry, active_config)
        raw['v7_registry'] = registry
        raw['watchlists'] = json.loads((ROOT / 'config/theme_watchlists.json').read_text(encoding='utf-8')) if approved_config.get('enabled') else raw.get('watchlists') or json.loads((ROOT / 'config/theme_watchlists.json').read_text(encoding='utf-8'))
        if not approved_config.get('enabled'):
            raw['source_configuration'] = json.loads((ROOT / 'config/sources.json').read_text(encoding='utf-8'))
        raw['v7_mode'] = True
        _rehydrate_index_universes(raw)
        required_symbols = set(active_config.get('anchors', {}).values())
        required_symbols.update(str(member.get('ticker', '')).upper() for record in raw['watchlists'].get('watchlists', []) for member in record.get('members', []))
        required_symbols.update(registry.get('context_symbols', ['SPY', 'QQQ', 'IWM']))
        required_symbols.update(registry.get('volatility_symbols', ['^VIX']))
        for universe in raw.get('v5', {}).get('mapped_universes', {}).values():
            required_symbols.update(symbol for company in universe.get('companies', []) for symbol in company.get('symbols', []))
        raw.setdefault('errors', {})['charts'] = {key: value for key, value in raw.get('errors', {}).get('charts', {}).items() if key in required_symbols}
        raw.setdefault('v5', {})['chart_errors'] = {key: value for key, value in raw.get('v5', {}).get('chart_errors', {}).items() if key in required_symbols}
        raw['v5']['iwm_breadth_errors'] = {key: value for key, value in raw.get('v5', {}).get('iwm_breadth_errors', {}).items() if key in required_symbols}
        snapshot['settings'] = dict(registry.get('settings', snapshot.get('settings', {})))
        snapshot['settings']['configured_active_anchor_count'] = len(active_config.get('anchors', {}))
        _ensure_v61_market_records(snapshot, raw, registry)
        snapshot['score_methodology'] = registry.get('score_methodology', {})
        snapshot['ui_configuration'] = registry.get('ui', {})
        snapshot['methodology_version'] = registry.get('methodology_version', registry.get('registry_version'))
        for theme in snapshot.get('themes', []):
            configured = next((t for t in registry['themes'] if t.get('id') == theme.get('id') and t.get('anchor') == theme.get('anchor')), {})
            theme.setdefault('level', configured.get('level', 'Theme'))
        prepare_registry_themes(snapshot, raw, registry)
        for theme in snapshot.get('themes', []):
            configured = next((t for t in registry['themes'] if t['id'] == theme['id']), {})
            theme.setdefault('level', configured.get('level', 'Theme'))
        enrich(snapshot, raw)
        if snapshot.get("context") and snapshot.get("session_date") and all(
            symbol in raw.get("charts", {}) for symbol in ("SPY", "QQQ")
        ):
            apply_v5(snapshot, raw)
            if not approved_config.get("enabled"):
                _retain_iwm_breadth(snapshot, raw, ROOT)
            if args.import_run and not approved_config.get("enabled"):
                _retain_imported_index_metrics(snapshot, imported_context)
        if raw.get('v7_mode'):
            snapshot['sources'] = {
                'price_provider': 'Alpaca SIP (split EMA / split+dividend returns)' if approved_config.get('enabled') and not args.import_run else 'Retained historical source',
                'index_universes': {key: value.get('url') for key, value in raw.get('v5', {}).get('index_universes', {}).items()},
                'partial': bool(raw.get('errors', {}).get('charts') or raw.get('v5', {}).get('chart_errors') or raw.get('v5', {}).get('iwm_breadth_errors')),
            }
        apply_v6(snapshot, raw, registry)
        apply_historical_ranks(snapshot, raw)
        apply_watchlists(snapshot, raw, raw['watchlists'])
        if approved_config.get('enabled'):
            from src.themescope.approved_rules import apply as apply_approved
            apply_approved(snapshot, raw)
            snapshot['run_kind'] = 'offline_historical_diagnostic' if args.import_run else 'live'
            snapshot['data_complete'] = bool(snapshot.get('data_complete')) and not args.import_run
            snapshot['publication_scope'] = 'local_only'
        snapshot['methodology_version'] = 'approved-1' if approved_config.get('enabled') else '7.1'
        snapshot['schema_version'] = '7.1'
        from src.themescope.cache import manifest_for_inputs
        raw['cache_manifest'] = manifest_for_inputs(raw, snapshot.get('collection_completed_at') or attempted)
        generated_dt = datetime.now(timezone.utc)
        generated_hkt = generated_dt.astimezone(ZoneInfo('Asia/Hong_Kong'))
        snapshot['dashboard_generated_at'] = generated_dt.isoformat(timespec='seconds')
        snapshot['dashboard_generated_at_hkt'] = generated_hkt.isoformat(timespec='seconds')
        snapshot['dashboard_generated_at_hkt_display'] = generated_hkt.strftime('%d %b %Y, %I:%M %p HKT').lstrip('0')
        snapshot['dashboard_display_timezone'] = 'Asia/Hong_Kong'
        validate(snapshot, raw)
        if approved_config.get('enabled') and not args.import_run:
            configured_anchors = json.loads((ROOT/'config/active_anchors.json').read_text())['anchors']
            if {t['id']:t['anchor'] for t in snapshot['themes']} != configured_anchors:
                raise ValueError('Active anchor cohort changed during refresh; activation/deactivation is prohibited.')
            if not snapshot.get('data_complete'):
                raise ValueError('Full manifest completeness required for live publication.')
        with tempfile.TemporaryDirectory(prefix='.themescope-stage-', dir=output.parent) as tmp:
            stage = Path(tmp) / 'run'
            stage.mkdir()
            _generate(snapshot, raw, stage)
            _write_json(stage / 'refresh_status.json', {'status': 'offline_diagnostic' if snapshot.get('run_kind') == 'offline_historical_diagnostic' else 'success', 'data_complete': snapshot.get('data_complete', False), 'attempted_at': attempted, 'data_date': snapshot['session_date'], 'imported': bool(args.import_run)})
            # Commit only generated files; preserve unrelated files in a custom output directory.
            # Dashboard is published last, after every dependent download is ready.
            output.mkdir(parents=True, exist_ok=True)
            backup = Path(tmp) / 'previous'
            backup.mkdir()
            changed = []
            files = sorted(stage.iterdir(), key=lambda p: p.name == 'dashboard.html')
            retired_files = ('sectors.csv', 'industries.csv', 'watchlist_15.csv', 'tradingview_15.txt')
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
        print(f"{'OFFLINE DIAGNOSTIC' if snapshot.get('run_kind') == 'offline_historical_diagnostic' else 'SUCCESS'}: data date {snapshot['session_date']}; {len(snapshot['themes'])} eligible ETF anchors across {len(snapshot.get('registry_diagnostics', []))} registry records; {sum(len(t['selected']) for t in snapshot['themes'])} stock selections.")
        bundle_name = 'diagnostic_bundle.zip' if snapshot.get('run_kind') == 'offline_historical_diagnostic' else 'run_bundle.zip'
        if approved_config.get('enabled'):
            from src.themescope.approved_data import record_attempt
            attempt_report = record_attempt(ROOT/'cache/approved_attempts.jsonl', kind='offline' if args.import_run else 'historical' if args.as_of else 'live', entered_collection=entered_collection, target=snapshot['session_date'], data_complete=bool(snapshot.get('data_complete')), publication_pass=not bool(args.import_run), elapsed=time.perf_counter()-launched_at)
            _write_json(output/'latest_attempt.json', attempt_report)
        print(f"Open {output / 'dashboard.html'}\nDownload bundle: {output / bundle_name}")
        return 0
    except KeyboardInterrupt:
        if approved_config.get('enabled'):
            from src.themescope.approved_data import record_attempt
            record_attempt(ROOT/'cache/approved_attempts.jsonl', kind='offline' if args.import_run else 'historical' if args.as_of else 'live', entered_collection=entered_collection, target=snapshot.get('session_date'), data_complete=False, publication_pass=False, elapsed=time.perf_counter()-launched_at, cancelled=True)
        raise
    except Exception as exc:
        if approved_config.get('enabled'):
            from src.themescope.approved_data import record_attempt
            record_attempt(ROOT/'cache/approved_attempts.jsonl', kind='offline' if args.import_run else 'historical' if args.as_of else 'live', entered_collection=entered_collection, target=snapshot.get('session_date'), data_complete=bool(snapshot.get('data_complete')), publication_pass=False, elapsed=time.perf_counter()-launched_at, detail=type(exc).__name__+': '+str(exc))
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
