#!/usr/bin/env python3
"""Run the deterministic ThemeScope v7.1 release acceptance audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.themescope.release_audit import audit_release  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, help="Generated latest_snapshot.json to validate")
    parser.add_argument("--registry-audit", type=Path, help="Generated registry_audit.csv to validate")
    parser.add_argument("--output", type=Path, help="Optional path for the machine-readable JSON report")
    args = parser.parse_args(argv)
    report = audit_release(
        ROOT,
        args.snapshot.resolve() if args.snapshot else None,
        args.registry_audit.resolve() if args.registry_audit else None,
    )
    encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else (Path.cwd() / args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    sys.stdout.write(encoded)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
