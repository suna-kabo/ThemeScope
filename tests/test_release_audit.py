from __future__ import annotations

import copy
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import scripts.audit_release as audit_release_command
from scripts.audit_release import main as audit_main
from src.themescope.release_audit import audit_release
from src.themescope.v6 import _source_status
from src.themescope.watchlists import build_reviewed_config

ROOT = Path(__file__).resolve().parents[1]


def _complete_config(root: Path) -> tuple[dict, dict]:
    registry = json.loads((root / "config/themes.json").read_text())
    active = json.loads((root / "config/active_anchors.json").read_text())["anchors"]
    names = {row["id"]: row for row in registry["themes"]}
    watchlists = []
    counter = 0
    for theme_id, anchor in sorted(active.items()):
        theme = names[theme_id]
        count = 20 if theme.get("level") == "Sector" else 15
        members = []
        for index in range(count):
            ticker = f"T{counter:04d}"
            counter += 1
            members.append({
                "ticker": ticker,
                "company": f"Operating Company {ticker}",
                "exchange": "NASDAQ-GS",
                "instrument_type": "operating_company",
                "relationship": "Core",
                "reason": f"Develops and sells products central to the {theme['name']} business group.",
                "maintenance": {
                    "date": "2026-10-15",
                    "source_type": "tradingview_universe",
                    "price_usd": 25.0,
                    "market_cap_usd": 3_000_000_000,
                    "adv30_usd": 30_000_000,
                    "adjusted_price_sessions": 220,
                },
            })
        watchlists.append({
            "theme_id": theme_id,
            "anchor": anchor,
            "status": "complete",
            "reviewed_date": "2026-10-24",
            "reviewed_candidate_count": count,
            "list_rationale": "Represents liquid leaders across the sector's major business groups." if count > 15 else None,
            "members": members,
        })
    return {"version": 2, "watchlists": watchlists}, {"registry": registry, "active": active, "names": names}


def _complete_snapshot(active: dict[str, str], names: dict) -> dict:
    diagnostics = [{"id": theme_id, "status": "selected_anchor", "candidates": [{"status": "eligible"}]}
                   for theme_id in active]
    inactive = sorted(set(names) - set(active))
    for index, theme_id in enumerate(inactive):
        candidate_count = 2 if index < 7 else 1
        diagnostics.append({
            "id": theme_id,
            "status": "inactive_this_run",
            "candidates": [{"status": "ineligible"} for _ in range(candidate_count)],
        })
    return {
        "themes": [
            {"id": theme_id, "theme_breadth21_pct": 60.0, "theme_breadth21_valid": 15,
             "theme_breadth50_pct": 50.0, "theme_breadth50_valid": 15}
            for theme_id in active
        ],
        "registry_diagnostics": diagnostics,
        "source_status": {"theme_watchlists": {"status": "complete"}},
    }


class ReleaseAuditTests(unittest.TestCase):
    def test_incomplete_configuration_fails_with_exact_unfinished_exposure_count(self):
        incomplete = json.loads((ROOT / "config/theme_watchlists.json").read_text())
        incomplete["watchlists"] = incomplete["watchlists"][:16]
        report = audit_release(ROOT, registry_audit_path=ROOT / "output/registry_audit.csv", watchlist_data=incomplete)
        self.assertFalse(report["passed"])
        self.assertEqual(report["summary"]["active_exposures"], 53)
        self.assertEqual(report["summary"]["inactive_exposures"], 12)
        self.assertEqual(report["summary"]["rejected_candidate_etf_rows"], 19)
        self.assertEqual(report["summary"]["theme_configuration_records"], 16)
        missing = [issue for issue in report["issues"] if issue["code"] == "missing_theme_record"]
        self.assertEqual(len(missing), 37)

    def test_complete_review_and_snapshot_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "config").mkdir()
            shutil.copy(ROOT / "config/themes.json", root / "config/themes.json")
            shutil.copy(ROOT / "config/active_anchors.json", root / "config/active_anchors.json")
            config, data = _complete_config(root)
            report = audit_release(root, snapshot_data=_complete_snapshot(data["active"], data["names"]), watchlist_data=config)
        self.assertTrue(report["passed"], report["issues"][:5])
        self.assertEqual(report["summary"]["list_status_counts"], {"complete": 53, "reviewed_short": 0, "reviewed_etf_only": 0})
        self.assertEqual(report["summary"]["rejected_candidate_etf_rows"], 19)
        self.assertEqual(report["summary"]["themes_with_valid_ema21_breadth"], 53)

    def test_nonfinal_status_blocks_publication(self):
        config, data = _complete_config(ROOT)
        changed = copy.deepcopy(config)
        changed["watchlists"][0]["status"] = "not_configured"
        report = audit_release(ROOT, watchlist_data=changed)
        self.assertFalse(report["passed"])
        self.assertTrue(any(issue["code"] == "nonfinal_status" for issue in report["issues"]))

    def test_source_status_is_complete_only_for_all_53_final_records(self):
        config, data = _complete_config(ROOT)
        themes = [{"id": theme_id, "anchor": anchor} for theme_id, anchor in data["active"].items()]
        raw = {"v7_mode": True, "watchlists": config, "v5": {"index_universes": {}}}
        source = _source_status(raw, {"themes": themes})["theme_watchlists"]
        self.assertEqual(source["status"], "complete")
        self.assertEqual(source["configured_lists"], 53)
        raw["watchlists"] = {"watchlists": config["watchlists"][:1]}
        source = _source_status(raw, {"themes": themes})["theme_watchlists"]
        self.assertEqual(source["status"], "incomplete")
        self.assertEqual(source["incomplete_lists"], 52)

    def test_reviewed_membership_keeps_candidate_and_reason_source_urls(self):
        active = json.loads((ROOT / "config/active_anchors.json").read_text())["anchors"]
        first = sorted(active)[0]
        review = {
            "reviewed_date": "2026-10-25",
            "themes": [
                {
                    "theme_id": theme_id,
                    "status": "reviewed_short",
                    "reviewed_candidate_count": 1,
                    "exception_reason": "A narrow reviewed list after full eligibility screening.",
                    "members": ([{
                        "ticker": "AAA",
                        "relationship": "Core",
                        "reason": "Builds a distinct product central to this reviewed exposure.",
                        "maintenance": {"date": "2026-10-15", "source_type": "anchor_etf"},
                        "source_url": "https://example.test/etf-holdings",
                        "reason_source_url": "https://example.test/company/AAA",
                    }] if theme_id == first else []),
                }
                for theme_id in sorted(active)
            ],
        }
        config = build_reviewed_config(
            {"proposals": [{"ticker": "AAA", "company": "Alpha", "exchange": "NYSE", "instrument_type": "operating_company"}]},
            review,
            json.loads((ROOT / "config/themes.json").read_text())["themes"],
            active,
        )
        member = next(row for row in config["watchlists"] if row["theme_id"] == first)["members"][0]
        self.assertEqual(member["source_url"], "https://example.test/etf-holdings")
        self.assertEqual(member["reason_source_url"], "https://example.test/company/AAA")

    def test_audit_command_returns_nonzero_for_incomplete_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "config").mkdir()
            for name in ("themes.json", "active_anchors.json"):
                shutil.copy(ROOT / "config" / name, root / "config" / name)
            (root / "config/theme_watchlists.json").write_text(json.dumps({"version": 2, "watchlists": []}))
            output = io.StringIO()
            with patch.object(audit_release_command, "ROOT", root), redirect_stdout(output):
                status = audit_main([])
        self.assertEqual(status, 1)
        self.assertFalse(json.loads(output.getvalue())["passed"])


if __name__ == "__main__":
    unittest.main()
