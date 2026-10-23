"""Deterministic manifests for the source payloads retained in a run bundle."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def manifest_for_inputs(raw: dict[str, Any], default_retrieved_at: str) -> list[dict[str, Any]]:
    """Record source identity, retrieval/effective dates, and a content hash.

    Source adapters currently retain their normalized response payloads rather
    than the original HTTP byte streams. The explicit payload kind prevents the
    hash from being mistaken for a wire-response hash.
    """
    rows: list[dict[str, Any]] = []

    def add(group: str, key: str, value: dict[str, Any], provider: str) -> None:
        if not isinstance(value, dict):
            return
        observations = value.get("observations") or []
        effective = value.get("as_of") or value.get("effective_date") or value.get("session_date")
        if effective is None and observations:
            effective = observations[-1].get("date")
        rows.append({
            "source": provider,
            "dataset": group,
            "key": key,
            "url": value.get("url"),
            "retrieved_at": value.get("retrieved_at") or default_retrieved_at,
            "effective_asof": effective,
            "payload_kind": "normalized_source_payload",
            "sha256": _digest(value),
        })

    providers = {
        "charts": "Yahoo Finance chart API",
        "holdings": "ETF issuer holdings source",
        "comparison_holdings": "ETF issuer holdings source",
        "quotes": "Nasdaq quote summary",
        "sec_annual_checks": "SEC EDGAR submissions",
    }
    for group, provider in providers.items():
        for key, value in sorted((raw.get(group) or {}).items()):
            add(group, str(key), value, provider)
    v5 = raw.get("v5") or {}
    for group, provider in (("charts", "Yahoo Finance chart API"), ("index_universes", "Index constituent provider"), ("security_mapping", "SEC issuer/listing map")):
        if group == "security_mapping":
            value = v5.get(group)
            if isinstance(value, dict):
                add("v5." + group, "company_tickers_exchange", value, provider)
            continue
        for key, value in sorted((v5.get(group) or {}).items()):
            add("v5." + group, str(key), value, provider)
    return rows
