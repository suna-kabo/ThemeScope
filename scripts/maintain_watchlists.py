#!/usr/bin/env python3
"""Import a TradingView scanner CSV and create a human-review proposal only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.themescope.watchlists import propose_import, read_watchlists  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path, help='TradingView scanner export CSV')
    parser.add_argument('--output', type=Path, default=Path('output/watchlist_proposals.json'), help='Proposal JSON path; approved config is never overwritten')
    args = parser.parse_args(argv)
    if not args.input.is_file():
        parser.error(f'Input CSV does not exist: {args.input}')
    registry = json.loads((ROOT / 'config/themes.json').read_text(encoding='utf-8'))
    config, _ = read_watchlists(ROOT / 'config/theme_watchlists.json', int(registry['settings'].get('watchlist_capacity', 20)))
    filters = dict(registry['settings'].get('watchlist_stock_filters', {}))
    filters['watchlist_capacity'] = registry['settings'].get('watchlist_capacity', 20)
    cap_path = ROOT / 'cache' / 'market_cap.json'
    try:
        filters['market_cap_cache'] = json.loads(cap_path.read_text(encoding='utf-8')).get('symbols', {})
    except (OSError, ValueError, TypeError):
        filters['market_cap_cache'] = {}
    proposal = propose_import(args.input, config, registry.get('themes', []), filters)
    output = args.output if args.output.is_absolute() else (Path.cwd() / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proposal, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    summary = [
        '# TradingView watchlist proposal', '',
        f"Input: `{proposal['input_file']}`; rows: {proposal['input_rows']}; proposals: {proposal['proposed_count']}; rejected by supplied filters: {proposal['rejected_count']}.",
        '', 'This file contains suggestions only. It does not edit `config/theme_watchlists.json`.',
        '', f"Theme column: {proposal.get('theme_column') or 'not present; assign a theme during review' }.",
        f"Theme assignment required: {str(proposal.get('theme_assignment_required')).lower()}.",
        '', 'Market cap or history checks missing from the CSV are marked for review. Price, average volume, and daily bars do not prove theme relevance.',
        '', 'The approved watchlist configuration remains unchanged.',
    ]
    output.with_suffix('.md').write_text('\n'.join(summary) + '\n', encoding='utf-8')
    print(f"Wrote review-only proposal: {output}")
    print('Approved watchlist configuration unchanged.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
