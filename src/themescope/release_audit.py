"""Deterministic acceptance audit for a ThemeScope v7.1 release."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any


FINAL_STATUSES = {"complete", "reviewed_short", "reviewed_etf_only"}
MEMBER_SOURCES = {"anchor_etf", "tradingview_universe", "outside_etf_addition"}
GENERIC_REASON_PARTS = (
    "retained from", "existing watchlist", "belongs to the sector", "belongs to this sector",
    "appears in the etf", "included in the etf", "established listed company classified",
    "selected for liquidity", "represents the theme", "relevant company",
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _generic_reason(reason: Any) -> bool:
    text = " ".join(str(reason or "").casefold().split())
    return not text or any(part in text for part in GENERIC_REASON_PARTS) or len(text) < 24


def audit_release(
    root: Path,
    snapshot_path: Path | None = None,
    registry_audit_path: Path | None = None,
    snapshot_data: dict[str, Any] | None = None,
    watchlist_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the release totals and every deterministic blocking issue."""
    registry = _read_json(root / "config/themes.json")
    active_config = _read_json(root / "config/active_anchors.json")
    watchlist_config = watchlist_data if watchlist_data is not None else _read_json(root / "config/theme_watchlists.json")
    themes = {row.get("id"): row for row in registry.get("themes", []) if row.get("id")}
    active = active_config.get("anchors", {})
    active_ids = set(active)
    candidate_etfs = set(active.values())
    for theme in themes.values():
        candidate_etfs.update(str(row.get("ticker") or "").upper() for row in theme.get("candidate_anchors", []) if isinstance(row, dict))
        candidate_etfs.update(str(row).upper() for row in theme.get("candidate_anchors", []) if isinstance(row, str))

    issues: list[dict[str, str]] = []

    def fail(code: str, message: str) -> None:
        issues.append({"code": code, "message": message})

    if len(active_ids) != 53:
        fail("active_universe_count", f"Expected 53 active exposures; found {len(active_ids)}.")
    inactive_ids = set(themes) - active_ids
    if len(inactive_ids) != 12:
        fail("inactive_exposure_count", f"Expected 12 inactive exposures; found {len(inactive_ids)}.")

    records = watchlist_config.get("watchlists", [])
    by_id: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_id.setdefault(str(record.get("theme_id") or ""), []).append(record)
    for theme_id, rows in sorted(by_id.items()):
        if len(rows) != 1:
            fail("duplicate_theme_record", f"{theme_id or '(blank)'} has {len(rows)} watchlist records; exactly one is required.")
        if theme_id not in active_ids:
            fail("unknown_theme_record", f"Watchlist record {theme_id or '(blank)'} is not an active exposure.")

    counts = Counter()
    statuses = Counter()
    all_tickers: Counter[str] = Counter()
    valid_breadth21 = valid_breadth50 = 0
    minimum_price = float(registry.get("settings", {}).get("watchlist_stock_filters", {}).get("raw_close_floor_usd", 15))
    minimum_cap = float(registry.get("settings", {}).get("watchlist_stock_filters", {}).get("market_cap_floor_usd", 2_000_000_000))
    minimum_adv = float(registry.get("settings", {}).get("watchlist_stock_filters", {}).get("adv30_floor_usd", 20_000_000))
    minimum_history = int(registry.get("settings", {}).get("ema_warmup_sessions", {}).get("50", 200))

    for theme_id in sorted(active_ids):
        rows = by_id.get(theme_id, [])
        expected_anchor = active.get(theme_id)
        theme = themes.get(theme_id, {})
        level = theme.get("level", "Theme")
        if not rows:
            fail("missing_theme_record", f"{theme_id} has no watchlist record.")
            continue
        record = rows[0]
        if str(record.get("anchor") or "").upper() != str(expected_anchor or "").upper():
            fail("anchor_mismatch", f"{theme_id} watchlist anchor {record.get('anchor')!r} does not match {expected_anchor!r}.")
        status = str(record.get("status") or "")
        statuses[status or "missing_status"] += 1
        if status not in FINAL_STATUSES:
            fail("nonfinal_status", f"{theme_id} has nonfinal status {status or '(missing)'}.")
        members = record.get("members")
        if not isinstance(members, list):
            fail("members_not_list", f"{theme_id} members must be a list.")
            continue
        counts[theme_id] = len(members)
        tickers: set[str] = set()
        for member in members:
            ticker = str(member.get("ticker") or "").strip().upper()
            if not ticker:
                fail("missing_ticker", f"{theme_id} contains a member with no ticker.")
                continue
            if ticker in tickers:
                fail("duplicate_member", f"{theme_id} contains duplicate ticker {ticker}.")
            tickers.add(ticker)
            all_tickers[ticker] += 1
            company = str(member.get("company") or "").strip()
            exchange = str(member.get("exchange") or "").strip().upper()
            relationship = str(member.get("relationship") or "").strip()
            reason = member.get("reason")
            if not company:
                fail("missing_company", f"{theme_id}/{ticker} has no company name.")
            if not (exchange.startswith("NYSE") or exchange.startswith("NASDAQ")):
                fail("invalid_exchange", f"{theme_id}/{ticker} is not recorded as NYSE or Nasdaq listed.")
            if relationship not in {"Core", "Related"}:
                fail("invalid_relationship", f"{theme_id}/{ticker} relationship must be Core or Related.")
            if _generic_reason(reason):
                fail("generic_reason", f"{theme_id}/{ticker} needs a concise company-specific reason.")
            if ticker in candidate_etfs or str(member.get("instrument_type") or "").casefold() in {"etf", "fund", "mutual fund"}:
                fail("non_operating_instrument", f"{theme_id}/{ticker} is recorded as an ETF or fund, not an operating company.")
            if member.get("instrument_type") != "operating_company":
                fail("company_type_unverified", f"{theme_id}/{ticker} must be marked as an operating_company.")
            maintenance = member.get("maintenance")
            if not isinstance(maintenance, dict):
                fail("maintenance_missing", f"{theme_id}/{ticker} has no maintenance facts.")
                continue
            source_type = maintenance.get("source_type")
            if source_type not in MEMBER_SOURCES:
                fail("candidate_source_missing", f"{theme_id}/{ticker} has an invalid maintenance candidate source.")
            try:
                date.fromisoformat(str(maintenance.get("date")))
            except (TypeError, ValueError):
                fail("maintenance_date_missing", f"{theme_id}/{ticker} has no valid maintenance date.")
            for field, floor in (("price_usd", minimum_price), ("market_cap_usd", minimum_cap), ("adv30_usd", minimum_adv)):
                value = maintenance.get(field)
                if not isinstance(value, (int, float)) or value < floor:
                    fail("eligibility_floor", f"{theme_id}/{ticker} {field} does not meet the ${floor:,.0f} maintenance floor.")
            history = maintenance.get("adjusted_price_sessions")
            if not isinstance(history, int) or history < minimum_history:
                fail("price_history_short", f"{theme_id}/{ticker} has fewer than {minimum_history} adjusted-price sessions.")

        size = len(members)
        if status == "complete":
            if level == "Sector" and size != 20:
                fail("sector_size", f"{theme_id} complete sector lists must contain 20 members; found {size}.")
            elif not 15 <= size <= 20:
                fail("complete_list_size", f"{theme_id} complete lists must contain 15 to 20 members; found {size}.")
            if size > 15 and not str(record.get("list_rationale") or "").strip():
                fail("expanded_list_rationale", f"{theme_id} lists above 15 need a business-group coverage rationale.")
        elif status == "reviewed_short":
            if not 1 <= size < 15 or level == "Sector" and size < 15:
                fail("reviewed_short_size", f"{theme_id} reviewed_short size is inconsistent with its list type ({size}).")
            if _generic_reason(record.get("exception_reason")):
                fail("short_exception_reason", f"{theme_id} needs a specific reviewed-short exception reason.")
            candidate_count = record.get("reviewed_candidate_count")
            if not isinstance(candidate_count, int) or candidate_count < size:
                fail("short_candidate_count", f"{theme_id} needs a reviewed candidate count at least as large as its member count.")
        elif status == "reviewed_etf_only":
            if size != 0:
                fail("etf_only_members", f"{theme_id} reviewed_etf_only record must have no stock members.")
            if _generic_reason(record.get("exception_reason")):
                fail("etf_only_exception_reason", f"{theme_id} needs a specific ETF-only exception reason.")
            if not isinstance(record.get("reviewed_candidate_count"), int) or record["reviewed_candidate_count"] < 1:
                fail("etf_only_candidate_count", f"{theme_id} needs a positive reviewed candidate count.")

    overlaps = {ticker: n for ticker, n in all_tickers.items() if n > 1}
    inactive_rows = None
    if registry_audit_path and registry_audit_path.is_file():
        with registry_audit_path.open(newline="", encoding="utf-8-sig") as handle:
            audit_rows = list(csv.DictReader(handle))
        inactive_rows = sum(row.get("status") != "selected_anchor" for row in audit_rows)
        inactive_row_ids = {row.get("id") for row in audit_rows if row.get("status") != "selected_anchor"}
        if inactive_rows and not inactive_row_ids.issubset(inactive_ids):
            fail("inactive_candidate_registry", "Rejected registry candidate rows include an exposure classified as active.")
        if inactive_rows != 19:
            fail("rejected_candidate_row_count", f"Expected 19 rejected candidate ETF rows; found {inactive_rows}.")

    snapshot = snapshot_data
    if snapshot is None and snapshot_path and snapshot_path.is_file():
        snapshot = _read_json(snapshot_path)
    if snapshot is not None:
        if inactive_rows is None:
            rejected_candidates = [
                candidate
                for exposure in snapshot.get("registry_diagnostics", [])
                if exposure.get("status") != "selected_anchor"
                for candidate in exposure.get("candidates", [])
                if candidate.get("status") != "eligible"
            ]
            inactive_rows = len(rejected_candidates)
            if inactive_rows != 19:
                fail("rejected_candidate_row_count", f"Expected 19 rejected candidate ETF rows; found {inactive_rows}.")
        snapshot_themes = {row.get("id"): row for row in snapshot.get("themes", [])}
        if set(snapshot_themes) != active_ids:
            fail("snapshot_active_universe", f"Generated snapshot has {len(snapshot_themes)} themes; expected all {len(active_ids)} active exposures.")
        for theme_id, row in snapshot_themes.items():
            if row.get("theme_breadth21_valid") is not None and row.get("theme_breadth21_pct") is not None:
                valid_breadth21 += 1
            if row.get("theme_breadth50_valid") is not None and row.get("theme_breadth50_pct") is not None:
                valid_breadth50 += 1
        source_status = snapshot.get("source_status", {}).get("theme_watchlists", {}).get("status")
        if source_status != "complete":
            fail("snapshot_source_status", f"Snapshot theme_watchlists source status is {source_status!r}, not complete.")

    return {
        "schema_version": "7.1",
        "passed": not issues,
        "summary": {
            "active_exposures": len(active_ids),
            "inactive_exposures": len(inactive_ids),
            "rejected_candidate_etf_rows": inactive_rows,
            "theme_configuration_records": len(records),
            "list_status_counts": {status: statuses.get(status, 0) for status in ("complete", "reviewed_short", "reviewed_etf_only")},
            "unique_stocks": len(all_tickers),
            "overlapping_stocks": len(overlaps),
            "additional_overlapping_memberships": sum(n - 1 for n in overlaps.values()),
            "themes_with_valid_ema21_breadth": valid_breadth21,
            "themes_with_valid_ema50_breadth": valid_breadth50,
            "watchlist_sizes": dict(sorted(counts.items())),
        },
        "issues": issues,
    }
