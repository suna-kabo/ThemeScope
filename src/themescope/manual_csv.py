"""Deterministic, network-free TradingView CSV release pipeline."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .approved_rules import STATES, breadth_state, canonical_decision, market_direction, price_state, priority
from .ranking import average_ranks


ROLES = ("stock", "etf", "spy", "qqq", "iwm")


def _header(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().casefold()
    text = text.replace("×", "x").replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text)
    return text


ALIASES = {
    "symbol": ("symbol", "ticker"),
    "description": ("description", "company", "company name", "name"),
    "price": ("price", "close", "last"),
    "change_1d_pct": ("price change %, 1 day", "change %, 1 day", "1 day change %", "change %"),
    "market_cap": ("market capitalization", "market cap"),
    "performance_1w_pct": ("performance %, 1 week", "performance %, 1w", "performance 1w %"),
    "performance_1m_pct": ("performance %, 1 month", "performance %, 1m", "performance 1m %"),
    "performance_3m_pct": ("performance %, 3 months", "performance %, 3m", "performance 3m %"),
    "industry": ("industry",),
    "sector": ("sector",),
    "exchange": ("exchange", "listing exchange"),
    "ema21": ("ema21 daily", "ema 21 daily", "exponential moving average (21) 1 day", "exponential moving average, 21, 1 day", "ema21"),
    "ema50": ("ema50 daily", "ema 50 daily", "exponential moving average (50) 1 day", "exponential moving average, 50, 1 day", "ema50"),
    "atr14_pct": ("atr%14 daily", "atr % 14 daily", "average true range % (14) 1 day", "average true range %, 14, 1 day", "atr%14"),
    "turnover_1d": ("price x volume turnover 1d", "price x volume 1 day", "price x volume", "volume x price", "price x volume (turnover), 1 day"),
    "adv30": ("price x average volume 30 days", "price x average volume, 30 days", "price x average volume over 30 days", "price x average volume 30 day", "price x average volume, 30 days"),
    "relative_volume_1d": ("relative volume 1d", "relative volume 1 day", "relative volume at time", "relative volume, 1 day"),
    "earnings_date": ("upcoming earnings date", "earnings date"),
    "currency": ("price - currency", "currency"),
    "aum": ("assets under management", "aum"),
    "expense_ratio": ("expense ratio",),
    "asset_class": ("asset class",),
    "focus": ("focus",),
    "category": ("category",),
    "leverage": ("leverage",),
}

REQUIRED = {
    "stock": ("symbol", "description", "price", "change_1d_pct", "market_cap", "performance_1w_pct", "performance_1m_pct", "performance_3m_pct", "industry", "sector", "exchange", "ema21", "ema50", "atr14_pct", "turnover_1d", "adv30", "relative_volume_1d"),
    "etf": ("symbol", "description", "price", "change_1d_pct", "performance_1w_pct", "performance_1m_pct", "performance_3m_pct", "exchange", "ema21", "ema50", "atr14_pct", "turnover_1d", "relative_volume_1d"),
    "spy": ("symbol", "price", "ema21", "ema50"),
    "qqq": ("symbol", "price", "ema21", "ema50"),
    "iwm": ("symbol", "price", "ema21", "ema50"),
}

NUMERIC = {"price", "change_1d_pct", "market_cap", "performance_1w_pct", "performance_1m_pct", "performance_3m_pct", "ema21", "ema50", "atr14_pct", "turnover_1d", "adv30", "relative_volume_1d", "aum", "expense_ratio"}
POSITIVE = {"price", "ema21", "ema50"}
OPTIONAL = tuple(key for key in ALIASES if key not in {"symbol"})


class CSVValidationError(ValueError):
    pass


def _number(value: Any, *, required: bool = False, positive: bool = False) -> float | None:
    text = str(value or "").strip()
    if not text:
        if required:
            raise CSVValidationError("required numeric value is blank")
        return None
    cleaned = text.replace(",", "").replace("$", "").replace("%", "").strip()
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))(?:\s*([KMBT]))?", cleaned, re.I)
    if not match:
        raise CSVValidationError(f"invalid numeric value {text!r}")
    value = float(match.group(1)) * {None: 1, "K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}[match.group(2).upper() if match.group(2) else None]
    if not math.isfinite(value) or (positive and value <= 0):
        raise CSVValidationError(f"numeric value must be finite{' and positive' if positive else ''}: {text!r}")
    return value


def parse_csv(path: Path, role: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if role not in ROLES:
        raise ValueError(f"Unknown CSV role {role!r}")
    source = path.expanduser().resolve()
    if not source.is_file():
        raise CSVValidationError(f"{role}: file does not exist: {source}")
    with source.open(newline="", encoding="utf-8-sig") as handle:
        table = list(csv.reader(handle))
    if len(table) < 2:
        raise CSVValidationError(f"{role}: CSV must contain a header and at least one data row")
    headers = table[0]
    normalized = [_header(value) for value in headers]
    mapping: dict[str, int] = {}
    ignored_duplicates: list[dict[str, Any]] = []
    for canonical, aliases in ALIASES.items():
        alias_set = {_header(alias) for alias in aliases}
        matches = [i for i, value in enumerate(normalized) if value in alias_set or re.sub(r"\.\d+$", "", value) in alias_set]
        if matches:
            exact = [i for i in matches if normalized[i] in alias_set]
            chosen = (exact or matches)[0]
            mapping[canonical] = chosen
            for i in matches:
                if i != chosen:
                    ignored_duplicates.append({"canonical": canonical, "header": headers[i], "index": i})
    missing = [key for key in REQUIRED[role] if key not in mapping]
    if missing:
        raise CSVValidationError(f"{role}: missing required columns: {', '.join(missing)}")
    rows: list[dict[str, Any]] = []
    symbols: set[str] = set()
    for line_number, cells in enumerate(table[1:], 2):
        if not any(str(cell).strip() for cell in cells):
            continue
        def cell(key: str) -> str:
            index = mapping.get(key)
            return cells[index].strip() if index is not None and index < len(cells) else ""
        symbol = cell("symbol").upper().replace(".", "-")
        if not symbol:
            raise CSVValidationError(f"{role}: blank symbol on line {line_number}")
        if symbol in symbols:
            raise CSVValidationError(f"{role}: duplicate symbol {symbol} on line {line_number}")
        symbols.add(symbol)
        row: dict[str, Any] = {"symbol": symbol}
        for key in ALIASES:
            if key == "symbol" or key not in mapping:
                continue
            raw = cell(key)
            if key in NUMERIC:
                try:
                    # Breadth universes deliberately retain rows with blank
                    # Price/EMA cells in the denominator; those rows are
                    # excluded from the shared valid set during calculation.
                    row[key] = _number(raw, required=key in REQUIRED[role] and role in {"stock", "etf"}, positive=key in POSITIVE)
                except CSVValidationError as exc:
                    raise CSVValidationError(f"{role}: line {line_number}, {key}: {exc}") from exc
            else:
                if key in REQUIRED[role] and not raw:
                    raise CSVValidationError(f"{role}: blank required {key} on line {line_number}")
                row[key] = raw or None
        rows.append(row)
    if not rows:
        raise CSVValidationError(f"{role}: CSV has no data rows")
    audit = {
        "role": role,
        "path": str(source),
        "filename": source.name,
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "row_count": len(rows),
        "unique_symbol_count": len(symbols),
        "columns": headers,
        "canonical_columns": sorted(mapping),
        "ignored_duplicate_columns": ignored_duplicates,
        "missing_required_fields": [],
        "missing_optional_fields": sorted(set(OPTIONAL) - set(mapping)),
    }
    return rows, audit


def percentile(values: dict[str, float | None], minimum: int) -> dict[str, float | None]:
    valid = {key: value for key, value in values.items() if isinstance(value, (int, float)) and math.isfinite(value)}
    if len(valid) < max(2, minimum):
        return {key: None for key in values}
    if len(set(valid.values())) == 1:
        return {key: 50.0 if key in valid else None for key in values}
    result: dict[str, float | None] = {}
    for key, value in values.items():
        if key not in valid:
            result[key] = None
            continue
        rank = 1 + sum(other < value for other in valid.values()) + (sum(other == value for other in valid.values()) - 1) / 2
        result[key] = 100 * (rank - 1) / (len(valid) - 1)
    return result


def theme_score(current: float | None, medium: float | None) -> float | None:
    return 0.6 * current + 0.4 * medium if current is not None and medium is not None else None


def theme_state(current: float | None, medium: float | None) -> str | None:
    if current is None or medium is None:
        return None
    return STATES[(0 if current >= 50 else 2) + (0 if medium >= 50 else 1)]


def breadth(rows: list[dict[str, Any]], minimum: int = 0, coverage_floor: float = 0.8) -> dict[str, Any]:
    valid = [row for row in rows if all(isinstance(row.get(key), (int, float)) and math.isfinite(row[key]) and row[key] > 0 for key in ("price", "ema21", "ema50"))]
    denominator = len(rows)
    coverage = len(valid) / denominator if denominator else 0.0
    available = denominator > 0 and len(valid) >= minimum and coverage >= coverage_floor
    b21 = 100 * sum(row["price"] > row["ema21"] for row in valid) / len(valid) if available else None
    b50 = 100 * sum(row["price"] > row["ema50"] for row in valid) / len(valid) if available else None
    state = breadth_state(b21, b50)
    reason = None if available else f"Requires at least {minimum} valid rows and {coverage_floor:.0%} coverage; found {len(valid)}/{denominator}."
    return {
        "21": {"value": b21, "status": "valid" if available else "unavailable", "above_count": sum(row["price"] > row["ema21"] for row in valid), "valid_count": len(valid), "eligible_count": denominator, "configured_count": denominator, "coverage_pct": 100 * coverage, "reason": reason, "ema_period": 21},
        "50": {"value": b50, "status": "valid" if available else "unavailable", "above_count": sum(row["price"] > row["ema50"] for row in valid), "valid_count": len(valid), "eligible_count": denominator, "configured_count": denominator, "coverage_pct": 100 * coverage, "reason": reason, "ema_period": 50},
        "state": state,
        "valid_rows": len(valid),
        "denominator": denominator,
        "coverage_pct": 100 * coverage,
        "excluded_symbols": [row.get("symbol") for row in rows if row not in valid],
    }


def _returns(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        "5": {"value": row.get("performance_1w_pct") / 100 if row.get("performance_1w_pct") is not None else None, "status": "valid" if row.get("performance_1w_pct") is not None else "unavailable"},
        "21": {"value": row.get("performance_1m_pct") / 100 if row.get("performance_1m_pct") is not None else None, "status": "valid" if row.get("performance_1m_pct") is not None else "unavailable"},
        "63": {"value": row.get("performance_3m_pct") / 100 if row.get("performance_3m_pct") is not None else None, "status": "valid" if row.get("performance_3m_pct") is not None else "unavailable"},
    }


def _row_fields(row: dict[str, Any]) -> dict[str, Any]:
    close, ema21, ema50 = row.get("price"), row.get("ema21"), row.get("ema50")
    return {
        "price_close": close,
        "daily_change": row.get("change_1d_pct") / 100 if row.get("change_1d_pct") is not None else None,
        "ema21": ema21,
        "ema50": ema50,
        "above_ema21": close > ema21 if close is not None and ema21 is not None else None,
        "above_ema50": close > ema50 if close is not None and ema50 is not None else None,
        "price_vs_ema21_pct": 100 * (close / ema21 - 1) if close is not None and ema21 else None,
        "price_vs_ema50_pct": 100 * (close / ema50 - 1) if close is not None and ema50 else None,
        "price_state": price_state(close, ema21, ema50),
        "returns": _returns(row),
        "atr14_pct": row.get("atr14_pct"),
        "turnover_1d_usd": row.get("turnover_1d"),
        "adv30_usd": row.get("adv30"),
        "relative_volume_1d": row.get("relative_volume_1d"),
        "exchange": row.get("exchange"),
        "currency": row.get("currency"),
    }


def _session_valid(root: Path, session: str) -> bool:
    try:
        datetime.strptime(session, "%Y-%m-%d")
    except ValueError:
        return False
    calendar = json.loads((root / "config/calendars/xnys_2020_2035_v1.json").read_text(encoding="utf-8"))
    return session in {row["session"] for row in calendar.get("sessions", [])}


def build_release(root: Path, paths: dict[str, Path], session: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if set(paths) != set(ROLES):
        raise CSVValidationError("All five explicit roles are required: stock, etf, spy, qqq and iwm")
    if not _session_valid(root, session):
        raise CSVValidationError(f"{session!r} is not a valid configured US market session")
    parsed = {role: parse_csv(paths[role], role) for role in ROLES}
    rows = {role: value[0] for role, value in parsed.items()}
    audits = {role: value[1] for role, value in parsed.items()}
    active = json.loads((root / "config/active_anchors.json").read_text(encoding="utf-8"))["anchors"]
    registry = json.loads((root / "config/themes.json").read_text(encoding="utf-8"))
    watchlists = json.loads((root / "config/theme_watchlists.json").read_text(encoding="utf-8"))
    config_themes = {row["id"]: row for row in registry["themes"]}
    watch_by_id = {row["theme_id"]: row for row in watchlists["watchlists"]}
    etfs = {row["symbol"]: row for row in rows["etf"]}
    required_etfs = set(active.values()) | {"SPY", "QQQ", "IWM"}
    missing_etfs = sorted(required_etfs - set(etfs))
    if missing_etfs:
        raise CSVValidationError("etf: missing configured anchors/context symbols: " + ", ".join(missing_etfs))
    manual_config = json.loads((root / "config/manual_csv.json").read_text(encoding="utf-8"))
    sanity_ranges = manual_config["breadth_universe_sanity"]
    for role, limits in sanity_ranges.items():
        low, high = int(limits["minimum_rows"]), int(limits["maximum_rows"])
        if not low <= len(rows[role]) <= high:
            raise CSVValidationError(f"{role}: {len(rows[role])} rows falls outside configured sanity range {low}-{high}; files may be swapped")
    score_minimum = max(2, math.ceil(float(manual_config["theme_score_minimum_coverage"]) * len(active)))
    eligible = {theme_id: etfs[anchor] for theme_id, anchor in active.items() if etfs[anchor].get("performance_1m_pct") is not None and etfs[anchor].get("performance_3m_pct") is not None}
    current = percentile({theme_id: eligible.get(theme_id, {}).get("performance_1m_pct") for theme_id in active}, score_minimum)
    medium = percentile({theme_id: eligible.get(theme_id, {}).get("performance_3m_pct") for theme_id in active}, score_minimum)
    stock_rows = {row["symbol"]: row for row in rows["stock"]}
    themes: list[dict[str, Any]] = []
    for theme_id, anchor in active.items():
        source = etfs[anchor]
        a, b = current[theme_id], medium[theme_id]
        state = theme_state(a, b)
        record = watch_by_id.get(theme_id, {"members": []})
        selected = []
        breadth_inputs = []
        for slot, member in enumerate(record.get("members", [])[:int(manual_config["watchlist_capacity"])], 1):
            daily = stock_rows.get(member["ticker"])
            if daily:
                breadth_inputs.append(daily)
            fields = _row_fields(daily) if daily else {"price_close": None, "ema21": None, "ema50": None, "above_ema21": None, "above_ema50": None, "returns": {key: {"value": None, "status": "unavailable"} for key in ("5", "21", "63")}, "adv30_usd": None}
            selected.append({**member, **fields, "ticker": member["ticker"], "company": member.get("company") or member["ticker"], "theme_id": theme_id, "theme_name": config_themes.get(theme_id, {}).get("name", theme_id), "anchor": anchor, "membership_tag": member.get("relationship"), "membership_rationale": member.get("reason"), "membership_source": "Configured theme watchlist", "selection_slot": slot, "selection_queue": member.get("relationship"), "session_date": session, "sector": daily.get("sector") if daily else None, "industry": daily.get("industry") if daily else None, "market_cap_usd": daily.get("market_cap") if daily else None, "turnover_1d_usd": daily.get("turnover_1d") if daily else None, "relative_volume_1d": daily.get("relative_volume_1d") if daily else None, "atr14_pct": daily.get("atr14_pct") if daily else None, "earnings_date": daily.get("earnings_date") if daily else None, "metric_status": "available" if daily else "unavailable"})
        theme_breadth = breadth(breadth_inputs, minimum=int(manual_config["theme_breadth_minimum_valid"]), coverage_floor=float(manual_config["breadth_minimum_coverage"]))
        fields = _row_fields(source)
        name = config_themes.get(theme_id, {}).get("name", theme_id)
        has_members = bool(record.get("members"))
        score = theme_score(a, b)
        theme = {"id": theme_id, "name": name, "anchor": anchor, "ticker": anchor, "level": config_themes.get(theme_id, {}).get("level", "Theme"), **fields, "current_strength_score": a, "medium_strength_score": b, "theme_score": score, "theme_state": state, "selected": selected, "configured_watchlist_count": len(record.get("members", [])), "watchlist_member_count": len(record.get("members", [])), "watchlist_status": record.get("status", "configured"), "watchlist_reviewed_date": record.get("reviewed_date"), "has_watchlist": has_members, "stock_scope": "Configured watchlist" if has_members else "Reviewed ETF-only", "stock_drilldown_status": "available" if has_members else "reviewed_etf_only", "theme_watchlist_breadth": {"21": theme_breadth["21"], "50": theme_breadth["50"]}, "theme_breadth21_pct": theme_breadth["21"]["value"], "theme_breadth50_pct": theme_breadth["50"]["value"], "theme_breadth21_valid": theme_breadth["21"]["valid_count"], "theme_breadth50_valid": theme_breadth["50"]["valid_count"], "theme_breadth21_above": theme_breadth["21"]["above_count"], "theme_breadth50_above": theme_breadth["50"]["above_count"], "breadth_status_21": theme_breadth["21"]["status"], "breadth_status_50": theme_breadth["50"]["status"], "field_status": {key: {"status": "valid" if value is not None else "unavailable", "value": value} for key, value in (("current_strength_score", a), ("medium_strength_score", b), ("theme_score", score))}}
        themes.append(theme)
    ranks = average_ranks({row["id"]: row["theme_score"] for row in themes})
    index_metrics = {role: breadth(rows[role], coverage_floor=float(manual_config["breadth_minimum_coverage"])) for role in ("spy", "qqq", "iwm")}
    market_etfs = {symbol: etfs[symbol] for symbol in ("SPY", "QQQ", "IWM")}
    contexts = []
    for symbol, role in (("SPY", "spy"), ("QQQ", "qqq"), ("IWM", "iwm")):
        contexts.append({"ticker": symbol, "name": symbol, "instrument_type": "equity_market_etf", **_row_fields(market_etfs[symbol]), "index_breadth": {"21": index_metrics[role]["21"], "50": index_metrics[role]["50"]}, "breadth_state": index_metrics[role]["state"], "breadth_label": "Russell 2000 Breadth" if symbol == "IWM" else f"{symbol} Breadth"})
    context_by_symbol = {row["ticker"]: row for row in contexts}
    spy_breadth, qqq_breadth = index_metrics["spy"]["state"], index_metrics["qqq"]["state"]
    combined = spy_breadth if spy_breadth == qqq_breadth else "Mixed" if spy_breadth and qqq_breadth else None
    direction = market_direction(context_by_symbol["SPY"]["price_state"], context_by_symbol["QQQ"]["price_state"], combined)
    for row in themes:
        row["global_rank"] = row["rank_current"] = ranks[row["id"]]
        row["research_priority"] = priority(direction, row["theme_state"], row["price_close"], row["ema50"])
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    unmatched = [
        {"theme_id": record["theme_id"], "ticker": member["ticker"], "exchange": member.get("exchange")}
        for record in watchlists["watchlists"] for member in record.get("members", [])
        if member["ticker"] not in stock_rows
    ]
    configured_memberships = sum(len(record.get("members", [])) for record in watchlists["watchlists"])
    matched_memberships = configured_memberships - len(unmatched)
    state_counts = Counter(row["theme_state"] or "Unavailable" for row in themes)
    priority_counts = Counter(row["research_priority"]["label"] for row in themes)
    audit = {
        "schema_version": "manual-csv-1",
        "declared_us_session": session,
        "generation_timestamp_utc": generated,
        "inputs": audits,
        "input_valid": True,
        "anchor_complete": True,
        "configured_anchor_count": len(active),
        "anchor_present_count": len(active),
        "score_eligible_count": len(eligible),
        "score_excluded": sorted(set(active) - set(eligible)),
        "score_peer_set": sorted(eligible),
        "percentile_method": "ascending average rank; 100*(rank-1)/(N-1); all-equal=50",
        "price_states": {symbol: context_by_symbol[symbol]["price_state"] for symbol in ("SPY", "QQQ", "IWM")},
        "breadth": {"SPY": index_metrics["spy"], "QQQ": index_metrics["qqq"], "Russell 2000": index_metrics["iwm"], "combined": combined},
        "breadth_available": {"SPY": index_metrics["spy"]["state"] is not None, "QQQ": index_metrics["qqq"]["state"] is not None, "Russell 2000": index_metrics["iwm"]["state"] is not None},
        "market_classification": direction,
        "theme_state_counts": dict(state_counts),
        "priority_counts": dict(priority_counts),
        "configured_theme_list_sizes": {record["theme_id"]: len(record.get("members", [])) for record in watchlists["watchlists"]},
        "configured_memberships": configured_memberships,
        "stock_member_matches": matched_memberships,
        "unmatched_configured_members": unmatched,
        "unmatched_unique_symbols": sorted({row["ticker"] for row in unmatched}),
        "stock_metric_availability": {"matched": matched_memberships, "unmatched": len(unmatched)},
        "theme_breadth_available": sum(row["breadth_status_21"] == row["breadth_status_50"] == "valid" for row in themes),
        "publication_pass": False,
        "runtime_stages": {},
        "runtime_seconds": None,
    }
    generated_hkt = datetime.fromisoformat(generated).astimezone(ZoneInfo("Asia/Hong_Kong"))
    decision = canonical_decision(session, generated_hkt.isoformat(timespec="seconds"), contexts, themes, direction, combined)
    snapshot = {
        "schema_version": "manual-csv-1",
        "methodology_version": "manual-csv-1",
        "run_kind": "manual_csv",
        "session_date": session,
        "generated_at": generated,
        "dashboard_generated_at": generated,
        "dashboard_generated_at_hkt": generated_hkt.isoformat(timespec="seconds"),
        "dashboard_generated_at_hkt_display": generated_hkt.strftime("%d %b %Y, %I:%M %p HKT").lstrip("0"),
        "dashboard_display_timezone": "Asia/Hong_Kong",
        "settings": {**registry.get("settings", {}), "watchlist_capacity": int(manual_config["watchlist_capacity"]), "watchlist_default_limit": int(manual_config["watchlist_capacity"]), "configured_active_anchor_count": len(active)},
        "score_methodology": {"current": "TradingView 1-month Performance percentile", "medium": "TradingView 3-month Performance percentile", "theme_score_weights": {"current_strength": 0.6, "medium_strength": 0.4}, "state_threshold": 50, "method": "Cross-sectional ETF momentum from manual CSV"},
        "context": contexts,
        "volatility_context": [],
        "themes": themes,
        "market_classification": {"direction": direction, "combined_breadth": combined, "inputs": {symbol: {"price": context_by_symbol[symbol]["price_state"], "breadth": context_by_symbol[symbol]["breadth_state"]} for symbol in ("SPY", "QQQ", "IWM")}, "reason": decision["reason"], "action_summary": decision["action_sentence"], "decision": decision},
        "decision": decision,
        "ui_configuration": {"score_bands": [{"min": 0, "max": 25, "class": "score-q1"}, {"min": 25, "max": 50, "class": "score-q2"}, {"min": 50, "max": 75, "class": "score-q3"}, {"min": 75, "max": 100, "class": "score-q4"}]},
        "source_status": {"theme_watchlists": {"status": "complete"}},
        "data_complete": True,
        "publication_scope": "local_only",
        "manual_csv_audit": audit,
    }
    raw = {"source": "tradingview-csv", "input_audit": audits, "watchlists": watchlists, "network_requests": 0}
    return snapshot, raw
