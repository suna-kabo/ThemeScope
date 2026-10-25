from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from scripts.generate_dashboard import _retain_iwm_breadth
from src.themescope.price_cache import PriceCache
from src.themescope.watchlists import _breadth_metric, apply_watchlists, propose_import, validate_watchlists
from src.themescope.collect_v7 import build_snapshot_v7


def _dates(count: int) -> list[str]:
    end = date(2026, 10, 23)
    values = []
    cursor = end
    while len(values) < count:
        if cursor.weekday() < 5:
            values.append(cursor.isoformat())
        cursor -= timedelta(days=1)
    return list(reversed(values))


def _chart(symbol: str, dates: list[str], rising: bool = True) -> dict:
    rows = []
    for index, day in enumerate(dates):
        close = 50 + index if rising else 500 - index
        rows.append({'date': day, 'close': float(close), 'adj_close': float(close), 'volume': 1_000_000.0})
    return {'symbol': symbol, 'observations': rows, 'meta': {'symbol': symbol, 'instrumentType': 'EQUITY', 'currency': 'USD'}, 'events': {'splits': {}}, 'retrieved_at': '2026-10-24T00:00:00+00:00'}


class WatchlistConfigTests(unittest.TestCase):
    def test_many_to_many_membership_and_biotechnology_are_supported(self):
        config = {'watchlists': [
            {'theme_id': 'theme-ai', 'anchor': 'AIQ', 'members': [{'ticker': 'NVDA', 'relationship': 'Core', 'reason': 'AI chips'}]},
            {'theme_id': 'theme-biotechnology', 'anchor': 'XBI', 'members': [{'ticker': 'NVDA', 'relationship': 'Related', 'reason': 'Biotech compute exposure'}]},
        ]}
        result = validate_watchlists(config)
        self.assertEqual(result['theme-ai']['members'][0]['ticker'], 'NVDA')
        self.assertEqual(result['theme-biotechnology']['members'][0]['relationship'], 'Related')

    def test_invalid_duplicate_missing_reason_and_capacity_rejected(self):
        base = {'theme_id': 'theme-one', 'anchor': 'ETF'}
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            validate_watchlists({'watchlists': [{**base, 'members': [
                {'ticker': 'AAA', 'relationship': 'Core', 'reason': 'Relevant'},
                {'ticker': 'AAA', 'relationship': 'Related', 'reason': 'Also relevant'},
            ]}]})
        with self.assertRaisesRegex(ValueError, 'short reason'):
            validate_watchlists({'watchlists': [{**base, 'members': [{'ticker': 'AAA', 'relationship': 'Core', 'reason': ''}]}]})
        members = [{'ticker': f'T{i}', 'relationship': 'Core', 'reason': 'Relevant'} for i in range(21)]
        with self.assertRaisesRegex(ValueError, 'capacity'):
            validate_watchlists({'watchlists': [{**base, 'members': members}]})

    def test_breadth_80_percent_boundary_and_failure_reasons(self):
        calendar = _dates(260)
        members = [{'ticker': f'S{i}', 'relationship': 'Core', 'reason': 'Relevant'} for i in range(15)]
        charts = {f'S{i}': _chart(f'S{i}', calendar, i < 10) for i in range(12)}
        settings = {'ema_periods': [21, 50], 'ema_warmup_sessions': {'21': 84, '50': 200}, 'ema_slope_sessions': 5, 'minimum_breadth_sample': 8, 'minimum_breadth_coverage': .8}
        exact = _breadth_metric(members, charts, calendar, calendar[-1], 21, settings)
        self.assertEqual(exact['status'], 'valid')
        self.assertEqual((exact['above_count'], exact['valid_count'], exact['configured_count']), (10, 12, 15))
        charts.pop('S11')
        low_coverage = _breadth_metric(members, charts, calendar, calendar[-1], 21, settings)
        self.assertEqual(low_coverage['reason_code'], 'price_coverage_low')
        for ticker in list(charts)[7:]:
            charts.pop(ticker)
        too_few = _breadth_metric(members, charts, calendar, calendar[-1], 21, settings)
        self.assertEqual(too_few['reason_code'], 'too_few_valid_members')
        self.assertEqual(_breadth_metric([], charts, calendar, calendar[-1], 21, settings)['reason_code'], 'not_configured')

    def test_membership_changes_do_not_change_score_and_missing_watchlist_does_not_suppress_anchor(self):
        calendar = _dates(260)
        charts = {'AAA': _chart('AAA', calendar)}
        theme = {'id': 'theme-one', 'name': 'One', 'anchor': 'ETF', 'theme_score': 71.5, 'theme_state': 'Leading', 'rank_current': 2, 'selected': []}
        snapshot = {'session_date': calendar[-1], 'settings': {'watchlist_capacity': 20, 'ema_periods': [21, 50], 'ema_warmup_sessions': {'21': 84, '50': 200}, 'ema_slope_sessions': 5, 'minimum_breadth_sample': 8, 'minimum_breadth_coverage': .8}, 'themes': [theme]}
        apply_watchlists(snapshot, {'charts': charts, 'session_calendar': calendar}, {'version': 1, 'watchlists': []})
        self.assertEqual(theme['theme_score'], 71.5)
        self.assertEqual(theme['rank_current'], 2)
        self.assertEqual(theme['watchlist_unavailable_reason'], 'Theme watchlist is not configured.')
        self.assertEqual(theme['theme_watchlist_breadth']['21']['reason_code'], 'not_configured')
        self.assertIsNone(theme['theme_breadth21_pct'])
        self.assertEqual(theme['theme_breadth21_above'], 0)
        self.assertEqual(theme['theme_breadth21_valid'], 0)

    def test_tradingview_csv_produces_review_diff_without_mutating_config(self):
        config = {'version': 1, 'watchlists': [{'theme_id': 'theme-one', 'anchor': 'ONE', 'members': [{'ticker': 'AAA', 'relationship': 'Core', 'reason': 'Existing'}]}]}
        original = json.loads(json.dumps(config))
        themes = [{'id': 'theme-one', 'name': 'One', 'anchor': 'ONE'}]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'scan.csv'
            path.write_text('Ticker,Theme,Price,Average Volume,Market Cap\nNYSE:BBB,One,25,1000000,3000000000\nNYSE:AAA,One,40,1000000,4000000000\n', encoding='utf-8')
            proposal = propose_import(path, config, themes, {'raw_close_floor_usd': 15, 'adv30_floor_usd': 20_000_000, 'market_cap_floor_usd': 2_000_000_000})
        self.assertFalse(proposal['auto_overwrite'])
        self.assertEqual(proposal['theme_diffs'][0]['proposed_additions'], ['BBB'])
        self.assertEqual(proposal['theme_diffs'][0]['proposed_removals'], [])
        self.assertEqual(config, original)

    def test_candidate_import_uses_sector_industry_as_evidence_not_theme_assignment(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'universe.csv'
            path.write_text(
                'Symbol,Description,Price,Market capitalization,Industry,Sector,"Price × average volume, 30 days",Exchange,Perf 1M,Perf 3M\n'
                'NASDAQ:AAA,Alpha Systems,25,3B,Semiconductors,Information Technology,20M,NASDAQ-GS,999%,999%\n',
                encoding='utf-8',
            )
            proposal = propose_import(path, {'watchlists': []}, [{'id': 'theme-semiconductors', 'name': 'Semiconductors', 'anchor': 'SMH'}], {
                'require_complete_maintenance_data': True,
                'maintenance_date': '2026-10-15',
                'raw_close_floor_usd': 15,
                'market_cap_floor_usd': 2_000_000_000,
                'adv30_floor_usd': 20_000_000,
            })
        self.assertTrue(proposal['theme_assignment_required'])
        self.assertIsNone(proposal['proposals'][0]['matched_theme'])
        self.assertEqual(proposal['proposals'][0]['industry'], 'Semiconductors')
        self.assertEqual(proposal['proposals'][0]['maintenance']['market_cap_usd'], 3_000_000_000)
        self.assertEqual(proposal['proposals'][0]['maintenance']['adv30_usd'], 20_000_000)


class PriceCacheTests(unittest.TestCase):
    def test_normal_collector_requests_market_universes_but_no_company_research(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(Path(__file__).resolve().parents[1] / 'config', root / 'config')
            calendar = _dates(260)

            def cached_chart(_cache, symbol, _required_session, _fetcher, years=2, force=False):
                return _chart(symbol, calendar), 'hit', None

            spy = {'rows': [{'ticker': 'AAA', 'company': 'Alpha', 'company_id': 'AAA', 'security_type': 'EQUITY'}], 'retrieved_at': '2026-10-24T00:00:00+00:00'}
            qqq = {'rows': [{'ticker': 'BBB', 'company': 'Beta', 'company_id': 'BBB', 'security_type': 'EQUITY'}], 'retrieved_at': '2026-10-24T00:00:00+00:00'}
            iwm = {'rows': [{'ticker': 'CCC', 'company': 'Gamma'}], 'as_of': '2026-10-23', 'retrieved_at': '2026-10-24T00:00:00+00:00'}
            mapped_iwm = {'companies': [{'company_id': 'CCC', 'company': 'Gamma', 'symbols': ['CCC']}], 'symbols': ['CCC'], 'unresolved_mappings': [], 'excluded_rows': []}
            with patch('src.themescope.price_cache.PriceCache.get_or_fetch', autospec=True, side_effect=cached_chart), \
                    patch('src.themescope.collect_v7._fetch_spy_universe', return_value=spy), \
                    patch('src.themescope.collect_v7._fetch_qqq_universe', return_value=qqq), \
                    patch('src.themescope.collect_v7.fetch_holdings', return_value=iwm) as holdings, \
                    patch('src.themescope.collect_v7.map_iwm_universe', return_value=mapped_iwm):
                _snapshot, raw = build_snapshot_v7(root)

        self.assertEqual(raw['collection_request_counts']['filings'], 0)
        self.assertEqual(raw['collection_request_counts']['quotes'], 0)
        self.assertEqual(raw['collection_request_counts']['theme_holdings'], 0)
        self.assertEqual(raw['collection_request_counts']['aum_spread'], 0)
        self.assertEqual(holdings.call_count, 1)
        self.assertEqual(holdings.call_args.args[0]['anchor'], 'IWM')
        self.assertNotIn('security_mapping', raw['source_configuration'])
        self.assertNotIn('stock_market_metadata', raw['source_configuration'])

    def test_same_session_reuse_and_bounded_incremental_update(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = PriceCache(Path(folder))
            calls = []
            def fetch(symbol, **kwargs):
                calls.append((symbol, kwargs))
                if kwargs.get('start_date'):
                    return _chart(symbol, ['2026-10-22', '2026-10-23'])
                return _chart(symbol, ['2026-10-22'])
            first, result, error = cache.get_or_fetch('AAA', '2026-10-22', fetch)
            self.assertEqual(result, 'full_refresh')
            self.assertIsNone(error)
            reused, result, _ = cache.get_or_fetch('AAA', '2026-10-22', fetch)
            self.assertEqual(result, 'hit')
            self.assertEqual(len(calls), 1)
            updated, result, error = cache.get_or_fetch('AAA', '2026-10-23', fetch)
            self.assertEqual(result, 'incremental_update')
            self.assertEqual(calls[-1][1]['end_date'], '2026-10-23')
            self.assertEqual(max(row['date'] for row in updated['observations']), '2026-10-23')
            self.assertEqual(cache.stats['requests'], 2)

    def test_malformed_response_keeps_prior_valid_series(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = PriceCache(Path(folder))
            chart = _chart('AAA', ['2026-10-22'])
            cache.write('AAA', chart, full_refresh_at='2026-10-22T00:00:00+00:00')
            result, status, error = cache.get_or_fetch('AAA', '2026-10-23', lambda *_args, **_kwargs: {'symbol': 'AAA', 'observations': []})
            self.assertEqual(status, 'stale_reused')
            self.assertIsNotNone(error)
            self.assertEqual(result['observations'], chart['observations'])
            self.assertEqual(cache.read('AAA')['chart']['observations'], chart['observations'])

    def test_stale_iwm_breadth_keeps_its_observation_session(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / 'cache' / 'aggregates' / 'iwm_breadth.json'
            path.parent.mkdir(parents=True)
            previous = {'session_date': '2026-10-22', 'breadth': {str(period): {'status': 'valid', 'value': 50.0, 'above_count': 10, 'valid_count': 20, 'eligible_count': 20} for period in (21, 50)}, 'change_5_pp': {'21': 1.0, '50': -2.0}}
            path.write_text(json.dumps(previous), encoding='utf-8')
            snapshot = {'session_date': '2026-10-23', 'context': [{'ticker': 'IWM', 'index_breadth': {str(period): {'status': 'unavailable', 'value': None} for period in (21, 50)}, 'field_status': {}}]}
            _retain_iwm_breadth(snapshot, {'v7_mode': True}, root)
            market = snapshot['context'][0]
            self.assertTrue(market['index_breadth_stale'])
            self.assertEqual(market['index_breadth_observation_date'], '2026-10-22')
            self.assertIn('2026-10-22', market['index_breadth']['21']['reason'])

    def test_older_import_cannot_restore_newer_iwm_breadth(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / 'cache' / 'aggregates' / 'iwm_breadth.json'
            path.parent.mkdir(parents=True)
            previous = {'session_date': '2026-10-23', 'breadth': {str(period): {'status': 'valid', 'value': 60.0, 'above_count': 12, 'valid_count': 20, 'eligible_count': 20} for period in (21, 50)}}
            path.write_text(json.dumps(previous), encoding='utf-8')
            original = path.read_text(encoding='utf-8')
            snapshot = {'session_date': '2026-10-22', 'context': [{'ticker': 'IWM', 'index_breadth': {str(period): {'status': 'unavailable', 'value': None} for period in (21, 50)}, 'field_status': {}}]}
            _retain_iwm_breadth(snapshot, {'v7_mode': True}, root)
            market = snapshot['context'][0]
            self.assertEqual(path.read_text(encoding='utf-8'), original)
            self.assertEqual(market['index_breadth_observation_date'], '2026-10-22')
            self.assertFalse(market['index_breadth_stale'])


if __name__ == '__main__':
    unittest.main()
