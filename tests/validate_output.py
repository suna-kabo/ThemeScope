"""Validate v7.1 deliverables and their calculation contracts."""
import csv
import json
import math
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.themescope.ranking import average_ranks
from src.themescope.v5 import theme_state


out = Path(sys.argv[1]).resolve()
snapshot = json.loads((out / "latest_snapshot.json").read_text(encoding="utf-8"))
raw = json.loads((out / "raw_inputs.json").read_text(encoding="utf-8"))
registry = json.loads((ROOT / "config/themes.json").read_text(encoding="utf-8"))
anchors = json.loads((ROOT / "config/active_anchors.json").read_text(encoding="utf-8"))
watchlists = json.loads((ROOT / "config/theme_watchlists.json").read_text(encoding="utf-8"))
html = (out / "dashboard.html").read_text(encoding="utf-8")
assert snapshot.get("session_date")
assert snapshot.get("schema_version") == "7.1"
assert not {"holdings", "quotes", "sec_annual_checks", "evidence_freshness"} & set(raw)
assert not {"holdings", "mapped_universes", "iwm_breadth_diagnostics"} & set(raw.get("v5", {}))
assert not {"security_mapping", "stock_market_metadata", "etf_metadata"} & set(raw.get("source_configuration", {}))
assert "connect-src 'none'" in html
assert "candidate_metrics" not in html and "registry_diagnostics" not in html
assert "ETF holdings breadth" not in html

themes = snapshot.get("themes", [])
active = anchors.get("anchors", {})
assert len(active) == 53
assert {row["id"]: row["anchor"] for row in themes} == active
assert len({row["id"] for row in themes}) == len(themes)

ranking = average_ranks({row["id"]: row.get("theme_score") for row in themes})
weights = snapshot.get("score_methodology", {}).get("theme_score_weights", {})
threshold = snapshot.get("score_methodology", {}).get("state_threshold", 50)
memberships = {row["theme_id"]: row for row in watchlists.get("watchlists", [])}
minimum = int(snapshot["settings"].get("minimum_breadth_sample", 8))
coverage_floor = float(snapshot["settings"].get("minimum_breadth_coverage", 0.8))
for row in themes:
    score = row.get("theme_score")
    current, medium = row.get("current_strength_score"), row.get("medium_strength_score")
    if score is not None:
        assert current is not None and medium is not None
        assert math.isclose(score, weights["current_strength"] * current + weights["medium_strength"] * medium, abs_tol=1e-9)
    if current is not None and medium is not None:
        assert row.get("theme_state") == theme_state(current, medium, threshold)
    assert row.get("global_rank") == ranking[row["id"]]
    assert row.get("rank_current") == ranking[row["id"]]
    if row.get("rank_t_minus_5") is not None and row.get("rank_current") is not None:
        assert math.isclose(row["rank_change_5"], row["rank_t_minus_5"] - row["rank_current"], abs_tol=1e-9)
    configured = memberships.get(row["id"])
    expected = len(configured.get("members", [])) if configured and configured.get("anchor") == row["anchor"] else 0
    assert row.get("watchlist_member_count") == expected
    assert row.get("has_watchlist") is (expected > 0)
    for period in ("21", "50"):
        metric = row["theme_watchlist_breadth"][period]
        assert metric.get("configured_count") == expected
        if expected == 0:
            assert metric.get("reason_code") == "not_configured"
        if metric.get("status") == "valid":
            assert metric["valid_count"] >= minimum
            assert metric["valid_count"] / expected >= coverage_floor
            assert math.isclose(metric["value"], 100 * metric["above_count"] / metric["valid_count"], abs_tol=1e-9)

with (out / "themes.csv").open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    theme_columns = reader.fieldnames or []
    theme_rows = list(reader)
required = {
    "rank_current", "rank_t_minus_5", "rank_change_5", "type", "theme_id", "name", "anchor_etf", "state",
    "theme_score", "current_strength", "medium_strength", "return21_pct", "excess21_pp", "return63_pct",
    "excess63_pp", "theme_breadth21_pct", "theme_breadth21_above", "theme_breadth21_valid", "theme_breadth21_change_5_pp",
    "theme_breadth50_pct", "theme_breadth50_above", "theme_breadth50_valid", "theme_breadth50_change_5_pp",
    "configured_watchlist_count", "session_date", "generated_at",
}
assert required <= set(theme_columns)
assert not set(theme_columns) & {"coverage_pct", "theme_score_status", "price_source_url", "mandate_review_status"}
assert len(theme_rows) == len(themes)
by_id = {row["id"]: row for row in themes}
for row in theme_rows:
    source = by_id[row["theme_id"]]
    assert row["session_date"] == snapshot["session_date"]
    if source["returns"]["21"].get("value") is not None:
        assert math.isclose(float(row["return21_pct"]), 100 * source["returns"]["21"]["value"], abs_tol=1e-9)

with (out / "market.csv").open(encoding="utf-8-sig", newline="") as handle:
    market_columns = csv.DictReader(handle).fieldnames or []
assert {"return5_pct", "return21_pct", "return63_pct", "index_breadth21_pct", "index_breadth50_pct"} <= set(market_columns)
assert not set(market_columns) & {"coverage_pct", "sec_filing_status", "aum_status", "spread_status"}

with (out / "stock_diagnostics.csv").open(encoding="utf-8-sig", newline="") as handle:
    stock_reader = csv.DictReader(handle)
    stock_columns = stock_reader.fieldnames or []
    stock_rows = list(stock_reader)
assert len(stock_rows) == sum(len(row.get("selected", [])) for row in themes)
assert {"relationship", "reason", "adv30_usd", "return21_pct", "excess21_pp"} <= set(stock_columns)
assert not set(stock_columns) & {"filing_url", "accession_number", "membership_evidence_coverage", "agent_vote"}

report = (out / "watchlist_migration.md").read_text(encoding="utf-8")
assert "Final reviewed lists: 53/53 (complete 44; reviewed short 9; reviewed ETF-only 0)" in report
assert "Configured memberships: 772; unique stocks: 510; overlapping stocks: 175" in report
with (out / "membership_review.csv").open(encoding="utf-8-sig", newline="") as handle:
    membership_reader = csv.DictReader(handle)
    membership_columns = membership_reader.fieldnames or []
    membership_rows = list(membership_reader)
assert len(membership_rows) == sum(row.get("watchlist_member_count", 0) for row in themes)
assert {"theme_id", "status", "ticker", "relationship", "reason", "maintenance_date", "candidate_source", "reason_source_url"} <= set(membership_columns)
assert all(row["reason"] and row["relationship"] in {"Core", "Related"} for row in membership_rows)
assert len({row["ticker"] for row in membership_rows}) == 510
with zipfile.ZipFile(out / "run_bundle.zip") as bundle:
    assert bundle.testzip() is None
    names = set(bundle.namelist())
    assert {"dashboard.html", "themes.csv", "market.csv", "latest_snapshot.json", "raw_inputs.json", "theme_watchlists.json", "active_anchors.json", "market_breadth_prices.csv.gz", "watchlist_prices.csv.gz", "iwm_breadth_prices.csv.gz", "release_audit.json", "membership_review.csv", "theme_watchlist_summary.csv"} <= names

print(f"v7.1 output passed: {len(themes)} ranked exposures, {len(membership_rows)} reviewed memberships, session {snapshot['session_date']}.")
