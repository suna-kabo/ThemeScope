#!/usr/bin/env python3
"""Build or explicitly apply a reviewed ThemeScope watchlist configuration."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.themescope.release_audit import audit_release  # noqa: E402
from src.themescope.watchlists import build_reviewed_config, propose_import, read_watchlists  # noqa: E402


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _template(active: dict[str, str], themes: list[dict], reviewed_date: str, existing_config: dict, anchor_candidates: dict[str, list[dict]]) -> dict:
    by_id = {row.get("id"): row for row in themes}
    existing = {row.get("theme_id"): row for row in existing_config.get("watchlists", [])}
    output = []
    for theme_id, anchor in sorted(active.items()):
        members = {}
        for member in existing.get(theme_id, {}).get("members", []):
            ticker = str(member.get("ticker") or "").upper()
            if ticker:
                members[ticker] = {
                    "ticker": ticker, "company": member.get("company"), "exchange": member.get("exchange"),
                    "relationship": member.get("relationship"), "reason": member.get("reason"),
                }
        for candidate in anchor_candidates.get(theme_id, []):
            ticker = candidate["ticker"]
            members.setdefault(ticker, {
                "ticker": ticker, "company": candidate.get("company"), "exchange": candidate.get("exchange"),
                "relationship": None, "reason": None,
            })
            members[ticker]["maintenance"] = candidate.get("maintenance")
            members[ticker]["instrument_type"] = candidate.get("instrument_type")
            members[ticker]["source_url"] = candidate.get("source_url")
        output.append({
            "theme_id": theme_id,
            "name": by_id.get(theme_id, {}).get("name"),
            "anchor": anchor,
            "status": "review_required",
            "reviewed_candidate_count": 0,
            "exception_reason": None,
            "list_rationale": None,
            "members": list(members.values()),
        })
    return {
        "reviewed_date": reviewed_date,
        "themes": output,
    }


def _merge_anchor_candidates(proposal: dict, payload: dict, active: dict[str, str], maintenance_date: str, filters: dict) -> dict[str, list[dict]]:
    configured = payload.get("themes", {})
    if not isinstance(configured, dict):
        raise ValueError("Anchor candidate JSON must use a 'themes' object keyed by active theme ID")
    unknown = set(configured) - set(active)
    if unknown:
        raise ValueError(f"Anchor candidate JSON contains unknown themes: {sorted(unknown)}")
    by_ticker = {row["ticker"]: row for row in proposal.get("proposals", [])}
    grouped = {}
    minimum_price = float(filters.get("raw_close_floor_usd", 15))
    minimum_cap = float(filters.get("market_cap_floor_usd", 2_000_000_000))
    minimum_adv = float(filters.get("adv30_floor_usd", 20_000_000))
    minimum_history = int(filters.get("minimum_adjusted_history_sessions", 200))
    for theme_id, candidates in configured.items():
        seen = set()
        for row in candidates:
            ticker = str(row.get("ticker") or "").strip().upper()
            if not ticker or ticker in seen:
                raise ValueError(f"{theme_id}: blank or duplicate anchor ETF candidate ticker {ticker!r}")
            seen.add(ticker)
            maintenance = {
                "date": maintenance_date,
                "source_type": "anchor_etf",
                "price_usd": row.get("price_usd"),
                "market_cap_usd": row.get("market_cap_usd"),
                "adv30_usd": row.get("adv30_usd"),
                "adjusted_price_sessions": row.get("adjusted_price_sessions"),
            }
            failures = []
            for field, floor in (("price_usd", minimum_price), ("market_cap_usd", minimum_cap), ("adv30_usd", minimum_adv)):
                value = maintenance[field]
                if not isinstance(value, (int, float)) or value < floor:
                    failures.append(f"{field} missing or below ${floor:,.0f}")
            if not str(row.get("exchange") or "").upper().startswith(("NYSE", "NASDAQ")):
                failures.append("exchange is not NYSE or Nasdaq")
            if row.get("instrument_type") != "operating_company":
                failures.append("instrument is not verified as an operating company")
            history = maintenance["adjusted_price_sessions"]
            if not isinstance(history, int) or history < minimum_history:
                failures.append(f"fewer than {minimum_history} adjusted-price sessions")
            if failures:
                proposal.setdefault("rejected_anchor_candidates", []).append({"theme_id": theme_id, "ticker": ticker, "reasons": failures})
                proposal["rejected_count"] += 1
                continue
            candidate = by_ticker.get(ticker)
            if candidate:
                candidate.setdefault("anchor_etf_themes", []).append(theme_id)
            else:
                candidate = {
                    "ticker": ticker, "company": row.get("company"), "exchange": row.get("exchange"),
                    "instrument_type": row.get("instrument_type"),
                    "maintenance": maintenance, "candidate_source": "anchor_etf", "review_required": True,
                    "anchor_etf_themes": [theme_id],
                    "source_url": row.get("source_url"),
                    "filter_checks": {"price": "passed", "market_cap": "passed", "adv30": "passed", "history_63_and_ema50": "passed"},
                }
                proposal["proposals"].append(candidate)
                by_ticker[ticker] = candidate
                proposal["proposed_count"] += 1
            grouped.setdefault(theme_id, []).append(candidate)
    return grouped


def _write_membership_review(path: Path, config: dict) -> None:
    fields = (
        "theme_id", "anchor", "status", "ticker", "company", "exchange", "instrument_type",
        "relationship", "reason", "maintenance_date", "candidate_source", "price_usd",
        "market_cap_usd", "adv30_usd", "adjusted_price_sessions", "history_source",
        "history_as_of", "source_url", "reason_source_url",
    )
    rows = []
    for theme in config.get("watchlists", []):
        for member in theme.get("members", []):
            maintenance = member.get("maintenance") or {}
            rows.append({
                "theme_id": theme.get("theme_id"), "anchor": theme.get("anchor"), "status": theme.get("status"),
                "ticker": member.get("ticker"), "company": member.get("company"), "exchange": member.get("exchange"),
                "instrument_type": member.get("instrument_type"), "relationship": member.get("relationship"),
                "reason": member.get("reason"), "maintenance_date": maintenance.get("date"),
                "candidate_source": maintenance.get("source_type"), "price_usd": maintenance.get("price_usd"),
                "market_cap_usd": maintenance.get("market_cap_usd"), "adv30_usd": maintenance.get("adv30_usd"),
                "adjusted_price_sessions": maintenance.get("adjusted_price_sessions"), "source_url": member.get("source_url"),
                "history_source": maintenance.get("adjusted_price_history_source"),
                "history_as_of": maintenance.get("adjusted_price_history_as_of"),
                "reason_source_url": member.get("reason_source_url"),
            })
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_theme_summary(path: Path, config: dict, themes: list[dict]) -> None:
    names = {row.get("id"): row.get("name") for row in themes}
    fields = ("theme_id", "name", "anchor", "status", "member_count", "reviewed_candidate_count", "exception_reason")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in config.get("watchlists", []):
            writer.writerow({
                "theme_id": row.get("theme_id"), "name": names.get(row.get("theme_id")), "anchor": row.get("anchor"),
                "status": row.get("status"), "member_count": len(row.get("members", [])),
                "reviewed_candidate_count": row.get("reviewed_candidate_count"), "exception_reason": row.get("exception_reason"),
            })


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="TradingView candidate universe CSV")
    parser.add_argument("--output", type=Path, default=Path("output/watchlist_proposal.json"), help="Candidate proposal JSON")
    parser.add_argument("--review", type=Path, help="Completed human assignment map JSON; requires all 53 themes")
    parser.add_argument("--anchor-candidates", type=Path, help="Optional one-time ETF constituent candidate JSON; no retrieval occurs")
    parser.add_argument("--maintenance-date", default=date.today().isoformat(), help="Date represented by the maintenance inputs, YYYY-MM-DD")
    parser.add_argument("--apply", action="store_true", help="Apply the reviewed map only if the release audit passes")
    args = parser.parse_args(argv)
    if not args.input.is_file():
        parser.error(f"Input CSV does not exist: {args.input}")
    if args.apply and not args.review:
        parser.error("--apply requires --review with a completed assignment map")
    try:
        date.fromisoformat(args.maintenance_date)
    except ValueError:
        parser.error("--maintenance-date must use YYYY-MM-DD")

    registry = json.loads((ROOT / "config/themes.json").read_text(encoding="utf-8"))
    active_config = json.loads((ROOT / "config/active_anchors.json").read_text(encoding="utf-8"))
    active = active_config.get("anchors", {})
    config, _ = read_watchlists(ROOT / "config/theme_watchlists.json", int(registry["settings"].get("watchlist_capacity", 20)))
    filters = dict(registry["settings"].get("watchlist_stock_filters", {}))
    filters.update({
        "watchlist_capacity": registry["settings"].get("watchlist_capacity", 20),
        "require_complete_maintenance_data": True,
        "maintenance_date": args.maintenance_date,
        "minimum_adjusted_history_sessions": registry["settings"].get("ema_warmup_sessions", {}).get("50", 200),
    })
    proposal = propose_import(args.input, config, registry.get("themes", []), filters)
    proposal["maintenance_date"] = args.maintenance_date
    anchor_candidates = {}
    if args.anchor_candidates:
        anchor_candidates = _merge_anchor_candidates(
            proposal, json.loads(args.anchor_candidates.read_text(encoding="utf-8")), active,
            args.maintenance_date, filters,
        )
    proposal["review_template"] = _template(active, registry.get("themes", []), args.maintenance_date, config, anchor_candidates)
    output = args.output if args.output.is_absolute() else (Path.cwd() / args.output).resolve()
    _write_json(output, proposal)
    template_path = output.with_name("watchlist_review_template.json")
    _write_json(template_path, proposal["review_template"])
    print(f"Candidate proposal: {output} ({proposal['proposed_count']} eligible candidates; {proposal['rejected_count']} rejected)")
    print(f"Review template: {template_path}; existing memberships and supplied anchor-ETF candidates are shown for review. Map candidates to one or more themes and record Core/Related plus a company-specific reason.")
    print("CSV performance columns are ignored; no membership choices are made from returns or momentum.")
    if not args.apply:
        print("Configuration unchanged. Use --review <completed-map.json> --apply only after all 53 lists have been reviewed.")
        return 0

    review = json.loads(args.review.read_text(encoding="utf-8"))
    reviewed = build_reviewed_config(proposal, review, registry.get("themes", []), active)
    audit = audit_release(ROOT, watchlist_data=reviewed)
    if not audit["passed"]:
        print(json.dumps(audit, indent=2, ensure_ascii=False), file=sys.stderr)
        print("Approved configuration unchanged: the reviewed proposal did not pass the release audit.", file=sys.stderr)
        return 1
    config_path = ROOT / "config/theme_watchlists.json"
    _write_json(config_path, reviewed)
    _write_membership_review(output.with_name("membership_review.csv"), reviewed)
    _write_theme_summary(output.with_name("theme_watchlist_summary.csv"), reviewed, registry.get("themes", []))
    _write_json(output.with_name("release_audit.json"), audit)
    print(f"Applied reviewed configuration: {config_path}")
    print(f"Membership review: {output.with_name('membership_review.csv')}")
    print(f"Theme summary: {output.with_name('theme_watchlist_summary.csv')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
