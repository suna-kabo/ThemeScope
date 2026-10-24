"""Validate the generated deliverables and cross-file calculation contracts."""
import csv
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.themescope.ranking import average_ranks
from src.themescope.v5 import theme_state


out = Path(sys.argv[1]).resolve()
snapshot = json.loads((out / "latest_snapshot.json").read_text(encoding="utf-8"))
config = json.loads(Path("config/themes.json").read_text(encoding="utf-8"))
html = (out / "dashboard.html").read_text(encoding="utf-8")
assert snapshot.get("session_date")
assert snapshot.get("schema_version") == "6.2"
assert "connect-src 'none'" in html
assert "candidate_metrics" not in html and "registry_diagnostics" not in html

diagnostics = snapshot.get("registry_diagnostics", [])
assert {row.get("id") for row in diagnostics} == {row.get("id") for row in config["themes"]}
assert all(row.get("candidates") for row in diagnostics)
selected = {row["id"]: row["selected_anchor"] for row in diagnostics if row.get("status") == "selected_anchor"}
ranked = {row["id"]: row.get("anchor") for row in snapshot.get("themes", [])}
assert ranked == selected
candidate_count = sum(len(row["candidates"]) for row in diagnostics)
assert candidate_count == sum(len(row.get("candidate_anchors", [])) for row in config["themes"])

current = average_ranks({row["id"]: row.get("theme_score") for row in snapshot.get("themes", [])})
weights = snapshot.get("score_methodology", {}).get("theme_score_weights", {})
threshold = snapshot.get("score_methodology", {}).get("state_threshold", 50)
for row in snapshot.get("themes", []):
    score = row.get("theme_score")
    c, m = row.get("current_strength_score"), row.get("medium_strength_score")
    if score is not None:
        assert c is not None and m is not None
        assert math.isclose(score, weights["current_strength"] * c + weights["medium_strength"] * m, abs_tol=1e-9)
    if c is not None and m is not None:
        assert row.get("theme_state") == theme_state(c, m, threshold)
    assert row.get("global_rank") == current[row["id"]]
    assert row.get("rank_current") == current[row["id"]]
    if row.get("rank_t_minus_5") is not None and row.get("rank_current") is not None:
        assert math.isclose(row["rank_change_5"], row["rank_t_minus_5"] - row["rank_current"], abs_tol=1e-9)
    if row.get("theme_score") is not None and not row.get("selected"):
        assert row.get("global_rank") is not None

for name in ("market.csv", "themes.csv", "stock_diagnostics.csv", "watchlist_15.csv", "watchlist_20.csv"):
    with (out / name).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        assert all(not re.fullmatch(r"return(?:5|21|63)", key) for key in columns), (name, columns)
        assert all(key not in columns for key in ("return1m_pct", "return3m_pct")), (name, columns)
        if name != "registry_audit.csv":
            assert all(f"return{window}_pct" in columns for window in ("5", "21", "63")), (name, columns)
        assert not any(re.fullmatch(r"excess(?:5|21|63)", key) for key in columns), (name, columns)

with (out / "registry_audit.csv").open(encoding="utf-8-sig", newline="") as handle:
    registry_rows = list(csv.DictReader(handle))
assert len(registry_rows) == candidate_count
assert {row.get("mandate_review_status") for row in registry_rows} <= {"reviewed", "rejected", "incomplete"}
assert all(row.get("mandate_review_status") in {"reviewed", "rejected"} for row in registry_rows)
assert all(row.get("mandate_review_date") and row.get("mandate_review_source", "").startswith("https://") and row.get("mandate_review_rationale") for row in registry_rows)
assert (out / "run_bundle.zip").is_file()
print(f"Generated output passed: {len(snapshot['themes'])} ranked exposures; {len(diagnostics)} registry records; {candidate_count} candidate audit rows; session {snapshot['session_date']}.")
