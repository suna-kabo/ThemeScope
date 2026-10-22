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
    theme_cfg = json.loads((root / "config/themes.json").read_text(encoding="utf-8"))
    evidence_cfg = json.loads((root / "config/evidence_reviews.json").read_text(encoding="utf-8"))
    errors = raw.get("errors", {})
    matrix: list[dict[str, str | None]] = []
    charts = raw.get("charts", {})
    chart_counts = [len(chart.get("observations", [])) for chart in charts.values()]
    chart_dates = [
        (chart.get("observations") or [])[0].get("date")
        for chart in charts.values()
        if chart.get("observations")
    ]
    latest_chart_dates = [
        (chart.get("observations") or [])[-1].get("date")
        for chart in charts.values()
        if chart.get("observations")
    ]
    history_desc = (
        f"{len(charts)} symbols; {min(chart_counts)}–{max(chart_counts)} daily bars, "
        f"source span {min(chart_dates)} to {max(latest_chart_dates)}"
        if chart_counts
        else "No history retrieved"
    )
    chart_error_count = len(errors.get("charts", {}))
    matrix.append(
        _source_row(
            "Daily raw close, volume, adjusted close, split events, dividend events",
            "SPY, QQQ, theme anchors, parent ETFs, reviewed stocks, anchor alternatives",
            "Yahoo Finance chart endpoint",
            "HTTPS JSON chart endpoint via stdlib urllib; 1-day interval, events=div,splits, includeAdjustedClose=true; sequential requests spaced 1.5 seconds apart to reduce throttling",
            history_desc,
            "Daily bars; the current session is accepted only after 16:30 America/New_York and a same-date provider market timestamp. Otherwise the prior completed session is used. No guaranteed publication delay.",
            "Endpoint is undocumented. Provider adjustment and publication semantics can change. It is not an exchange feed or a licensed data guarantee.",
            "Query2 uses the same Yahoo schema and adjustment convention. Hosts stop receiving requests after HTTP 429. If retrieval still fails, publication is rejected and a last successful export is retained with its original date.",
            f"{len(charts)}/{len(charts) + chart_error_count} requested chart series retrieved; {chart_error_count} error(s).",
            max((chart.get("retrieved_at") for chart in charts.values()), default=None),
            next((chart.get("url") for chart in charts.values() if chart.get("symbol") == "SPY"), "https://query1.finance.yahoo.com/v8/finance/chart/SPY"),
        )
    )
    calendar_symbol = raw.get("calendar_source_symbol")
    calendar_chart = charts.get(calendar_symbol) if calendar_symbol else None
    matrix.append(
        _source_row(
            "Shared US-session calendar and completed-session date",
            f"Selected reference {calendar_symbol or 'unavailable'}; benchmark remains SPY",
            "Yahoo Finance chart endpoint",
            "Use SPY session dates when available; otherwise QQQ, then the first available configured ETF anchor. SPY benchmark returns are never substituted.",
            f"{len(raw.get('session_calendar', []))} sessions through {raw.get('run_session') or 'unavailable'}" if raw.get("session_calendar") else "No calendar available",
            "Same-date bar is treated as final only after the 16:30 New York cutoff and a provider regular-market timestamp on that date.",
            "If SPY is unavailable, other price returns can remain valid but SPY-relative excess is unavailable. A fallback calendar does not replace the benchmark.",
            "No forward-fill or inferred sessions. If no ETF calendar is retrieved, session-dependent values stay unavailable.",
            f"Reference {calendar_symbol or 'unavailable'} retrieved." if calendar_chart else "No usable session-calendar history.",
            calendar_chart.get("retrieved_at") if calendar_chart else None,
            calendar_chart.get("url") if calendar_chart else None,
        )
    )
    matrix.append(
        _source_row(
            "Market capitalization, listing exchange, sector, industry",
            f"{len(raw.get('quotes', {}))} securities, including industry-only XBI screening",
            "Nasdaq quote summary API",
            "HTTPS JSON summary response; MarketCap, Exchange, Sector, Industry",
            "Current quote-summary retrieval on this run; per-field observation date is not supplied by provider.",
            "On-demand retrieval; the source publishes no separate cap-field timestamp or guaranteed refresh delay.",
            "A current summary response does not prove the market-cap field itself is no older than 35 days. Such values are provisional and timestamp uncertainty is shown.",
            "None. Missing cap, exchange, or industry blocks provisional stock eligibility.",
            f"{len(raw.get('quotes', {}))} ticker summaries retrieved; {len(errors.get('quotes', {}))} error(s).",
            max((quote.get("retrieved_at") for quote in raw.get("quotes", {}).values()), default=None),
            "https://api.nasdaq.com/api/quote/NVDA/summary?assetclass=stocks",
        )
    )
    sec = raw.get("sec_annual_checks", {})
    core_keys = {
        f"{member.get('theme_id')}:{member.get('ticker')}"
        for member in evidence_cfg.get("members", [])
        if member.get("category") == "Core business"
    }
    sec_statuses = [entry.get("status") for key, entry in raw.get("evidence_freshness", {}).items() if key in core_keys]
    sec_error_count = len(errors.get("sec", {}))
    filing_dates = [member.get("evidence", {}).get("filed_date") for member in evidence_cfg.get("members", []) if member.get("evidence", {}).get("filed_date")]
    matrix.append(
        _source_row(
            "Issuer business evidence and latest annual filing date check",
            f"{len(evidence_cfg.get('members', []))} dated evidence records; {len(sec)} unique CIK annual-feed checks",
            "SEC EDGAR company filings and submissions",
            "Retained annual-filing excerpt/source in config/evidence_reviews.json; latest 10-K/20-F/40-F rechecked through data.sec.gov submissions on every run",
            f"Evidence filing dates {min(filing_dates)} to {max(filing_dates)}; {sum(1 for status in sec_statuses if status == 'current')} current, {sum(1 for status in sec_statuses if status == 'stale')} stale, {sum(1 for status in sec_statuses if status == 'unavailable')} check unavailable.",
            "SEC submissions are available on demand; SEC feed publication may lag filing acceptance. This adapter checks annual forms only.",
            "Newer 8-K and other material disclosure content is not automatically classified. The theme-wide business review is explicitly incomplete; retained evidence remains provisional.",
            "None. A newer annual filing or unavailable freshness check excludes the issuer from provisional selection pending review.",
            f"{len(sec)} annual feeds checked; {sec_error_count} request error(s). Each evidence record links to its filing in config/evidence_reviews.json.",
            max((entry.get("retrieved_at") for entry in sec.values()), default=None),
            "https://www.sec.gov/edgar/search/",
        )
    )
    checks_by_cik = raw.get("sec_annual_checks", {})
    freshness_by_key = raw.get("evidence_freshness", {})
    for member in evidence_cfg.get("members", []):
        evidence = member.get("evidence") or {}
        cik = str(evidence.get("cik") or "")
        key = f"{member.get('theme_id')}:{member.get('ticker')}"
        freshness = freshness_by_key.get(key, {})
        latest = checks_by_cik.get(cik, {})
        if freshness.get("status") == "current":
            last_test = f"Pass: latest annual form {freshness.get('latest_annual_form')} filed {freshness.get('latest_annual_filed_date')} is not newer than the cited filing."
        elif freshness.get("status") == "stale":
            last_test = freshness.get("reason", "A newer annual filing needs review.")
        elif member.get("category") != "Core business":
            last_test = "Freshness check not run for unresolved evidence; issuer remains pending."
        else:
            last_test = freshness.get("reason", "Latest annual filing check unavailable.")
        matrix.append(
            _source_row(
                f"Business evidence filing: {member.get('ticker')}",
                f"{member.get('theme_id')} · {member.get('company')} · {member.get('category')}",
                "SEC EDGAR",
                f"{evidence.get('form') or 'No filing form'} company filing; sourced excerpt in config/evidence_reviews.json; annual form freshness check during run",
                f"Cited filing {evidence.get('filed_date') or 'date unavailable'}; latest annual form {freshness.get('latest_annual_form') or 'not checked'} {freshness.get('latest_annual_filed_date') or ''}".strip(),
                "Company filing and submissions feed are public; SEC acceptance and feed-update timing may vary.",
                "Evidence is limited to the cited excerpt and selected annual filing. 8-Ks are not automatically reviewed; theme membership screening is incomplete.",
                "None. Unresolved issuers stay pending; stale or unavailable annual freshness checks block provisional selection.",
                last_test,
                freshness.get("checked_at") or latest.get("retrieved_at"),
                evidence.get("url"),
            )
        )
    for theme_cfg_row in theme_cfg["themes"]:
        theme = next((item for item in snapshot["themes"] if item["id"] == theme_cfg_row["id"]), None)
        holdings = raw.get("holdings", {}).get(theme_cfg_row["anchor"])
        error = errors.get("holdings", {}).get(theme_cfg_row["anchor"])
        if holdings:
            holding_test = f"Retrieved {len(holdings.get('rows', []))} rows; as of {holdings.get('as_of') or 'date unavailable'}"
        else:
            holding_test = f"Unavailable: {error or 'no current holdings response'}"
        matrix.append(
            _source_row(
                "Official ETF holdings, tickers, weights, as-of date",
                f"{theme_cfg_row['name']} · {theme_cfg_row['anchor']}",
                theme_cfg_row["holdings_source"]["provider"],
                theme_cfg_row["holdings_source"]["method"],
                f"As of {holdings.get('as_of') or 'unavailable'}; {len(holdings.get('rows', [])) if holdings else 0} equity rows" if holdings else "No current holdings rows",
                "Issuer publication cadence varies; use the embedded source as-of date, not retrieval time, for freshness. A retrieval can contain an old snapshot.",
                "Complete-snapshot behavior is provider-specific. Parser failure is surfaced; no historical holdings list is substituted.",
                "VanEck can use its verified direct official dataset if fund-page discovery fails. An unrecovered retrieval failure rejects publication.",
                holding_test,
                holdings.get("retrieved_at") if holdings else None,
                theme_cfg_row["holdings_source"]["url"],
            )
        )
        matrix.append(
            _source_row(
                "ETF mandate, index, geography, weighting, plain-vanilla instrument review",
                f"{theme_cfg_row['name']} · {theme_cfg_row['anchor']}",
                theme_cfg_row["holdings_source"]["provider"],
                "Official fund page and mandate reviewed in the theme registry; no performance-weighted anchor score",
                "Mandate rationale and instrument review in config/themes.json",
                "Fund pages update on provider publication schedules; this prototype does not crawl a revision history.",
                "Mandate review is documented reviewer judgment and should be revisited if the fund objective changes.",
                "None. If the anchor mandate becomes unsuitable, its use requires a configuration review.",
                "Configured source and rationale; current instrument metadata checked with price retrieval." if theme else "Configuration source present; runtime price data unavailable.",
                snapshot.get("generated_at"),
                theme_cfg_row["anchor_url"],
            )
        )
    for comparison in snapshot.get("comparisons", []):
        holding = raw.get("comparison_holdings", {}).get(comparison["ticker"])
        error = errors.get("holdings", {}).get(comparison["ticker"])
        matrix.append(
            _source_row(
                "Alternative anchor holdings used for mandate/concentration comparison",
                f"{comparison['theme_id']} · {comparison['ticker']}",
                comparison["provider"],
                comparison["method"],
                f"As of {holding.get('as_of') or 'unavailable'}; {len(holding.get('rows', []))} holdings" if holding else "No current holdings rows",
                "Issuer publication cadence varies; displayed date is the source holdings as-of date.",
                comparison["comparison_note"],
                "None; comparison details are omitted when the source fails.",
                f"Retrieved {len(holding.get('rows', []))} rows; as of {holding.get('as_of') or 'unknown'}" if holding else f"Unavailable: {error or 'no response'}",
                holding.get("retrieved_at") if holding else None,
                comparison["holdings_url"],
            )
        )
    return matrix


EXPORT_COLUMNS = [
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
    lines = [
        "# ThemeScope run report",
        "",
        f"- **Run ID:** `{snapshot['run_id']}`",
        f"- **Generated:** {snapshot['generated_at']} UTC",
        f"- **Run date:** {snapshot['run_date']} (America/New_York)",
        f"- **Market session:** {snapshot['session_date'] or 'Unavailable'}",
        f"- **Registry:** `{snapshot['registry_version']}`",
        f"- **Source retrieval status:** {'Partial; see failures below.' if snapshot['sources']['partial'] else 'No retrieval failures reported.'}",
        "",
        "This is an on-demand snapshot. It does not refresh when the HTML is reopened. It is a watchlist organization tool, not a trading model or signal. The 15/20 selection convention is configurable and has not been validated as an investment strategy.",
        "",
        "## Theme coverage",
        "",
        "| Theme | Anchor | Official position rows / unique tickers | As of / status | Reviewed-subset eligible | Selected | Pending / unresolved | Excluded | Breadth summary | Eligible / selected / compact weight |",
        "|---|---|---:|---|---:|---:|---:|---:|---|---|",
    ]
    for theme in snapshot["themes"]:
        breadth = theme["breadth"]["above_ema21"]
        btext = breadth["label"]
        if breadth.get("fraction") is not None:
            btext += f" ({breadth.get('count')}/{breadth['valid_count']}, reviewed subset only)"
        else:
            btext += f" ({breadth.get('label_reason') or 'no valid denominator'})"
        weight_text = f"{theme['eligible_weight_pct']:.2f}% / {theme['selected_weight_pct']:.2f}% / {theme['visible15_weight_pct']:.2f}%"
        lines.append(
            f"| {theme['name']} | {theme['anchor']} | {theme['official_holdings_count']} / {theme['official_unique_ticker_count']} | {theme['holdings_source'].get('as_of') or 'unavailable'} / {theme['holdings_status']} | {theme['eligible_reviewed_count']} | {len(theme['selected'])} | {theme['pending_count']} ({theme['unresolved_evidence_count']} unresolved evidence) | {theme['excluded_count']} | {btext} | {weight_text} |"
        )
    lines += [
        "",
        f"Complete membership evidence screens: {sum(1 for theme in snapshot['themes'] if theme['review_complete'])}/{len(snapshot['themes'])}. Full-universe breadth summary labels are therefore unavailable. Subset fractions, where present, are selection-biased and do not replace full breadth.",
        "",
        "ETF holdings weights are fund net-asset weights and are not renormalized. Current holdings not reviewed or mapped remain in the pending table. Data eligibility failures remain in the exclusions table. ETF-only performance remains available separately when stock screening is incomplete.",
        "",
        "## Source and data limits",
        "",
        "- Yahoo chart is an accessible but undocumented endpoint. Adjusted close is used for total-return-compatible endpoint returns using Yahoo's provider convention; split-adjusted close is used for trend; raw contemporaneous close and volume are reconstructed from Yahoo split events for ADV$30. Provider definitions and publication behavior are not guaranteed.",
        f"- A current day bar is accepted only after the 16:30 America/New_York cutoff and a same-date Yahoo regular-market timestamp. Before then the prior verified session is used. The completed session is `{snapshot.get('session_date') or 'unavailable'}`.",
        "- Nasdaq's quote summary supplies market cap, listing exchange, sector, and industry, but exposes no timestamp for the market-cap field. The value is retrieved on this run; its field age cannot be independently proven. It is therefore a provisional eligibility input.",
        "- SEC submissions feeds are checked on each run for newer 10-K, 20-F, or 40-F filings than the cited evidence. Newer filings and unavailable checks block provisional selection. 8-K disclosure content is not automatically reviewed.",
        "- ETF holdings are retrieved from each fund issuer and retain the actual as-of date. Retrieval does not make an old snapshot current. Failed refreshes do not mix in old fields; the entire last successful dashboard is preserved with its original data date.",
        "- Theme evidence review is incomplete for every configured theme. The present curated lists are not full eligible universes; pending issuers, foreign mappings, and broader segment judgments remain unresolved.",
        "- XBI industry screening runs for mapped tickers. Biotechnology classifications are excluded by the default rule; non-biotechnology and unmapped holdings remain pending business-evidence review. Zero selections is not a claim that its eligible universe is empty.",
        "- Themes can overlap. Stock versus ETF excess is mechanically related where the fund owns the company; it is not independent alpha. No point-in-time membership, backtest, prediction, or execution quality assessment is provided.",
        "",
        "## Exports",
        "",
        f"- `watchlist_15.csv` / `watchlist_20.csv`: each theme's current compact or expanded selected list, with theme, selection reason, filing, weight, and metrics columns. CSV retains repeated tickers under different theme IDs.",
        f"- `tradingview_15.txt`: {tv15['unique']} unique exchange-qualified symbols; {tv15['duplicates']} cross-theme/listing duplicates collapsed; {tv15['omitted']} rows without confirmed NYSE/Nasdaq exchange omitted.",
        f"- `tradingview_20.txt`: {tv20['unique']} unique exchange-qualified symbols; {tv20['duplicates']} duplicates collapsed; {tv20['omitted']} rows without confirmed exchange omitted.",
        "- Browser exports use the active theme's filtered selected scope. CSV includes the theme field. TradingView text is flat and does not retain theme sections.",
        "- TradingView text uses one `EXCHANGE:TICKER` symbol per line and passed local syntax/mapping checks. The platform's import dialog was not exercised in this environment, so confirm behavior with the current TradingView client.",
        "",
        "## Retrieval failures",
        "",
    ]
    error_groups = raw.get("errors", {})
    any_errors = False
    for group, errors in error_groups.items():
        if not errors:
            continue
        any_errors = True
        lines.append(f"### {group.title()}")
        lines.append("")
        for symbol, error in sorted(errors.items()):
            lines.append(f"- `{symbol}`: {error}")
        lines.append("")
    if not any_errors:
        lines.append("No chart, quote, holdings, or SEC submissions retrieval errors were reported in this run.")
        lines.append("")
    lines += [
        "## Source matrix",
        "",
        "Download `source_matrix.csv` from this run for the field-level provider, access method, adjustment or as-of definition, history/delay, limitations, fallback, last test, and URL for each consumed source.",
        "",
        "## Regeneration",
        "",
        "From the repository root, run `python3 scripts/generate_dashboard.py` with network access. The script performs a fresh retrieval and writes the dashboard, JSON input snapshots, CSV and TradingView exports, source matrix, this report, and a ZIP bundle to the local `output/` directory. That directory is ignored by Git; generated runs are not committed or pushed to a branch. No database, service, secret, scheduled job, or paid package is used.",
        "",
    ]
    return "\n".join(lines)


RUN_OUTPUT_FILES = (
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
    matrix = snapshot.get("source_matrix") or make_source_matrix(snapshot, raw, ROOT)
    snapshot["source_matrix"] = matrix
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "latest_snapshot.json", snapshot)
    _write_json(output_dir / "raw_inputs.json", raw)
    _write_csv(output_dir / "source_matrix.csv", matrix, list(matrix[0].keys()) if matrix else [])

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
    parser.add_argument('--import-run', type=Path, help='Import a dated real run directory containing latest_snapshot.json and raw_inputs.json; no network requests')
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
            snapshot = json.loads((args.import_run / 'latest_snapshot.json').read_text(encoding='utf-8'))
            raw = json.loads((args.import_run / 'raw_inputs.json').read_text(encoding='utf-8'))
            if not snapshot.get('generated_at') or not snapshot.get('session_date'):
                raise ValueError('Imported run must retain its original generation time and session date')
            snapshot['imported_at'] = attempted
        else:
            print('Collecting official holdings, paced prices, quotes and filing checks. Please wait.', flush=True)
            snapshot, raw = build_snapshot(ROOT)
        enrich(snapshot, raw)
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
