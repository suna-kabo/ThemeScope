"""Freeze the audited legacy behavior before vNext, using synthetic inputs only."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.themescope.daily_lists import build
from src.themescope.local_history import apply
from src.themescope.manual_csv import build_release
from src.themescope.research_policy import market_truth_table

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/vnext_migration/legacy_main.json'
HEADER = [
    'Symbol', 'Description', 'Price', 'Price change %, 1 day',
    'Market capitalization', 'Performance %, 1 week', 'Performance %, 1 month',
    'Performance %, 3 months', 'Industry', 'Sector', 'Exchange',
    'Exponential moving average, 21, 1 day',
    'Exponential moving average, 50, 1 day', 'Average true range %, 14, 1 day',
    'Price × volume (turnover), 1 day', 'Average volume, 10 days',
    'Relative volume, 1 day', 'Upcoming earnings date',
]


def synthetic_inputs(folder):
    active = json.loads((ROOT / 'config/active_anchors.json').read_text())['anchors']
    watchlists = json.loads((ROOT / 'config/theme_watchlists.json').read_text())['watchlists']
    symbols = {
        'stock': sorted({m['ticker'] for t in watchlists if t['theme_id'] in active
                         for m in t['members']}),
        'etf': sorted(set(active.values()) | {'SPY', 'QQQ', 'IWM'}),
        **{role: ['TEST' + role.upper() + str(i) for i in range(count)]
           for role, count in [('spy', 500), ('qqq', 100), ('iwm', 2000)]},
    }
    paths = {}
    for role, tickers in symbols.items():
        paths[role] = folder / (role + '.csv')
        with paths[role].open('w', encoding='utf-8', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(HEADER)
            for index, ticker in enumerate(tickers):
                a, b = ((index % 17 - 4, index % 23 - 6) if role == 'stock'
                        else (index % 13 - 5, index % 19 - 8))
                writer.writerow([ticker, 'SYNTHETIC MIGRATION BASELINE', 100, 1,
                                 3e9, 2, a, b, 'Synthetic', 'Synthetic', 'NASDAQ',
                                 90, 80, 2, 3e7, 600000, 1, ''])
    return paths


class MigrationBaselineTests(unittest.TestCase):
    def test_all_market_matrix_cells_match_frozen_main(self):
        expected = json.loads(FIXTURE.read_text(encoding='utf-8'))['expected']
        self.assertEqual(market_truth_table(), expected['market_matrix'])

    def test_legacy_rank_history_and_primary_exports_match_audited_main(self):
        fixture = json.loads(FIXTURE.read_text(encoding='utf-8'))
        self.assertTrue(fixture['provenance']['synthetic'])
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            snapshot, _ = build_release(ROOT, synthetic_inputs(temporary), '2024-01-03')
            history = apply(snapshot, temporary / 'history',
                            ROOT / 'config/calendars/xnys_2020_2035_v1.json')
            files = build(snapshot, json.loads((ROOT / 'config/watchlist_exports.json').read_text()))
            actual = {
                'market_matrix': snapshot['decision']['market_matrix'],
                'market_direction': snapshot['market_classification']['direction'],
                'themes': [
                    {key: row.get(key) for key in (
                        'id', 'anchor', 'theme_score', 'global_rank',
                        'current_strength_score', 'medium_strength_score',
                        'etf_ema_classification', 'priority_change', 'rank_change_daily',
                    )} | {'priority': row['research_priority']['label']}
                    for row in snapshot['themes']
                ],
                'history': history,
                'primary_exports': {
                    row['file']: files[row['file']] for row in snapshot['export_manifest']
                    if row['role'] in {'individual_primary_research', 'daily_primary_research'}
                },
            }
            self.assertEqual(actual, fixture['expected'])


if __name__ == '__main__':
    unittest.main()
