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
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.themescope.collect import build_snapshot  # noqa: E402
from src.themescope.presentation import enrich, validate
from src.themescope.v5 import apply as apply_v5


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


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
        rows.append(dict(field=field, scope=scope, provider=provider, method=method, as_of=source.get('as_of'), retrieved_at=source.get('retrieved_at'), url=source.get('url'), limitations=limitations))
    add('Adjusted returns and split-adjusted closes/EMA; split events for ADV', 'SPY, QQQ, ETF anchors and accepted stocks', 'Yahoo Finance', 'Daily chart endpoint; sequential 1.5s default pacing, query2 fallback; stop host after HTTP 429', raw.get('charts', {}).get('SPY', {}), 'Undocumented provider convention. Only completed common US sessions. No silent adjustment substitution.')
    add('Breadth price histories', 'Mapped index and anchor constituents', 'Yahoo Finance', 'Same chart schema and EMA warmups as core; count companies once', next(iter(raw.get('v5', {}).get('charts', {}).values()), {}), 'Unmapped foreign listings remain missing in coverage; no guessed listing substitutions.')
    for symbol, source in raw.get('v5', {}).get('index_universes', {}).items():
        add('Index constituent universe', symbol, 'Nasdaq' if symbol == 'QQQ' else 'Wikipedia current S&P 500 constituent table', 'Reproducible constituent list; source rows retained', source, source.get('asof_basis', ''))
    add('Verified issuer/listing map', 'Company deduplication and ticker mapping', 'SEC', 'company_tickers_exchange.json; deterministic primary share class', raw.get('v5', {}).get('security_mapping', {}), 'SEC CIK identifies issuers. Unverified mappings are not invented; common company IDs are deduplicated.')
    for symbol, source in raw.get('holdings', {}).items():
        add('Official equity holdings', symbol, 'Fund issuer', 'Official JSON/HTML/CSV/XLSX adapter; actual as-of date retained', source, 'Breadth is equal-company participation, independent of watchlist curation. Excluded and unmapped rows recorded.')
    add('Market capitalization and stock eligibility', 'Accepted watchlist candidates', 'Nasdaq', 'Quote summary endpoint', next(iter(raw.get('quotes', {}).values()), {}), 'No separate market-cap field timestamp; stock eligibility remains provisional.')
    for theme in snapshot.get('themes', []):
        for member in theme.get('reviewed_universe', theme.get('selected', [])):
            source = {'url': member.get('membership_source') or member.get('evidence', {}).get('url'), 'as_of': member.get('reviewed_date')}
            add('Membership rationale', theme['id']+':'+member['ticker'], 'Recorded issuer/evidence source', member.get('membership_tag') or member.get('evidence_category'), source, member.get('membership_rationale') or member.get('evidence_note', ''))
    return rows


EXPORT_COLUMNS = [
    "membership_tag", "membership_source", "membership_rationale", "is_anchor_holding", "price_close", "return5", "excess5_pp", "above_ema21", "above_ema50",
    "theme", "theme_id", "anchor", "selection_slot", "selection_queue", "selection_queue_rank",
    "selection_reason", "ticker", "company", "exchange", "security_type", "evidence_category",
    "evidence_note", "evidence_url", "evidence_filed_date", "reviewed_date", "etf_weight_pct",
    "market_cap_usd", "market_cap_retrieved_at", "adv30_usd", "return21", "return63",
    "excess21_pp", "excess63_pp", "relative_state", "price_trend", "session_date", "chart_url",
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
                "session_date": stock.get("session_date"), "chart_url": chart_url,
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


def _run_report(snapshot: dict[str, Any], raw: dict[str, Any], matrix: list[dict[str, Any]], tv15: dict[str, int], tv20: dict[str, int]) -> str:
    lines = ['# ThemeScope v5 run report', '', f"Data session: {snapshot['session_date']}", f"Collected: {snapshot['generated_at']}", '', '## Market/index participation']
    for row in snapshot['context']:
        lines.append(f"- {row['ticker']}: {row.get('market_condition21', 'Unavailable')} / {row.get('market_condition50', 'Unavailable')}")
        for period in (21,50):
            m = row.get('index_breadth', {}).get(str(period), {})
            lines.append(f"  - EMA{period}: {m.get('above_count')}/{m.get('valid_count')}, eligible {m.get('eligible_count')}, coverage {m.get('coverage_pct')}%, as of {m.get('as_of')}; {m.get('status')}: {m.get('reason') or 'valid'}")
    lines += ['', '## Primary ETF registry']
    for row in snapshot['themes']:
        lines.append(f"- {row['name']} ({row['anchor']}), {row.get('level')}: score {row.get('theme_score')}; {row.get('theme_state')}; {len(row['selected'])} selected stocks.")
        for field in ('percentile_excess21','percentile_excess63','etf_breadth21_pct','etf_breadth50_pct','current_strength_score','medium_strength_score','theme_score'):
            item = row.get('field_status', {}).get(field, {})
            lines.append(f"  - {field}: {row.get(field)}; {item.get('status')}; {item.get('reason') or 'valid'}")
        universe = raw.get('v5', {}).get('mapped_universes', {}).get(row['anchor'], {})
        lines.append(f"  - {len(universe.get('excluded_rows', []))} excluded source rows; {len(universe.get('unresolved_mappings', []))} unresolved equity mappings remain in coverage denominator.")
    lines += ['', '## Methodology and limits', '- Scores require 10 valid primary ETF peers. Six registry ETFs are retained; no padding to manufacture percentile scores.', '- 70/30 relative-percentile/breadth horizon scores; 60/40 current/medium final score. Fixed conventions, not optimized or validated trading signals.', '- ETF and index breadth use complete sourced equity universes independently of curated watchlists; price coverage thresholds are 8 valid companies, 80%, 35-day freshness.', '- Nasdaq cap field timestamp is unavailable. Supported membership rationale is required; filings are mandatory only for records marked requires_filing_review.', '- Current constituents are observed snapshots, not point-in-time historical membership. Wikipedia S&P 500 as-of is the retrieval observation date, not an official rebalance date.', '- Unverified foreign listing mappings remain missing; no substitution with a US ticker sharing the same letters.', '- Optional constituent/stock metrics can be unavailable without invalidating core ETF returns. Mandatory core return/holdings or index-universe collection failures reject refresh publication.', '', '## Source errors', '```json', json.dumps({'core': raw.get('errors', {}), 'constituent_histories':raw.get('v5', {}).get('chart_errors', {})}, indent=2), '```', '', '## Local files', 'dashboard.html, market.csv, themes.csv, latest_snapshot.json, raw_inputs.json, source_matrix.csv, watchlist_15.csv, watchlist_20.csv, tradingview_15.txt, tradingview_20.txt, run_bundle.zip.', 'Opening HTML never retrieves data. Explicitly run python scripts/generate_dashboard.py. Failed refreshes preserve existing valid exports and write refresh_status.json/failed_refresh.md separately.']
    return '\n'.join(lines)+'\n'


RUN_OUTPUT_FILES = (
    "market.csv", "themes.csv",
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

    for filename, records in [('market.csv', snapshot.get('context', [])), ('themes.csv', snapshot.get('themes', []))]:
        flat = []
        for record in records:
            row = {k:v for k,v in record.items() if v is None or isinstance(v, (str,int,float,bool))}
            row['session_date'] = snapshot['session_date']
            row['generated_at'] = snapshot['generated_at']
            for key, item in record.get('field_status', {}).items():
                for part in ('status','reason','observation_count','session_date','input_version','above_count','valid_count','eligible_count','coverage_pct','peer_count'):
                    row[key+'_'+part] = item.get(part)
            for window in ('5','21','63'):
                row['return'+window] = _number(record.get('returns', {}).get(window))
                value = _number(record.get('excess_returns', {}).get(window))
                row['excess'+window+'_pp'] = value*100 if value is not None else None
            flat.append(row)
        columns = list(dict.fromkeys(k for row in flat for k in row))
        _write_csv(output_dir / filename, flat, columns)
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
    args = parser.parse_args(argv)
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
            snapshot['imported_at'] = attempted
        else:
            print('Collecting official holdings, paced prices, quotes and filing checks. Please wait.', flush=True)
            snapshot, raw = build_snapshot(ROOT)
        registry = json.loads((ROOT / 'config/themes.json').read_text(encoding='utf-8'))
        for theme in snapshot.get('themes', []):
            configured = next((t for t in registry['themes'] if t['id'] == theme['id'] and t['anchor'] == theme['anchor']), {})
            theme.setdefault('level', configured.get('level', 'Theme'))
        enrich(snapshot, raw)
        if snapshot.get("context") and snapshot.get("session_date"):
            apply_v5(snapshot, raw)
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
            try:
                for source in files:
                    target = output / source.name
                    if target.exists():
                        shutil.copy2(target, backup / source.name)
                    os.replace(source, target)
                    changed.append(source.name)
            except BaseException:
                for name in reversed(changed):
                    old = backup / name
                    if old.exists():
                        os.replace(old, output / name)
                    else:
                        (output / name).unlink(missing_ok=True)
                raise
            (output / 'failed_refresh.md').unlink(missing_ok=True)
        print(f"SUCCESS: data date {snapshot['session_date']}; {len(snapshot['themes'])} themes; {sum(len(t['selected']) for t in snapshot['themes'])} provisional stock selections.")
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
