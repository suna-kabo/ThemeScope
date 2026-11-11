"""Reproduce the legacy import fixture without downloading or retaining market data.

Issuer/theme identifiers are configuration facts; every price, volume, quote and
holding weight below is manufactured. All external fetchers are replaced before
the legacy builder runs. Original real fixtures remain in pre-migration Git history.
"""
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class FixtureClock(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 10, 22, 22, tzinfo=timezone.utc)
        return value.astimezone(tz) if tz else value.replace(tzinfo=None)


def generate(destination):
    from src.themescope.collect import build_snapshot
    from src.themescope.presentation import enrich
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    registry = json.loads((ROOT / 'config/themes.json').read_text())
    registry['settings']['maximum_holdings_age_days'] = 35  # Legacy fixture contract.
    # The old import fixture intentionally predates IWM availability. Its callers
    # exercise both adding unavailable IWM and retaining later valid IWM records.
    registry['context_symbols'] = ['SPY', 'QQQ']
    anchors = {'SMH', 'CIBR', 'ICLN', 'XAR', 'SKYY', 'XBI'}
    registry['themes'] = [t for t in registry['themes'] if t.get('anchor') in anchors]
    evidence = json.loads((ROOT / 'config/evidence_reviews.json').read_text())
    dates = [r['session'] for r in json.loads((ROOT / 'config/calendars/xnys_2020_2035_v1.json').read_text())['sessions']
             if r['session'] <= '2026-10-22'][-300:]
    by_anchor = {t['anchor']: [m['ticker'] for m in evidence['members'] if m['theme_id'] == t['id']]
                 for t in registry['themes']}
    etfs = anchors | {'SPY', 'QQQ', 'IWM'} | {t['parent_sector'] for t in registry['themes'] if t.get('parent_sector')}
    etfs |= {symbol for t in registry['themes'] for symbol in t.get('candidate_anchors', [])}
    stamp = '2026-10-22T22:00:00+00:00'

    def chart(symbol, **kwargs):
        slope = (int(hashlib.sha256(symbol.encode()).hexdigest()[:4], 16) % 9 + 1) / 100
        return {'symbol': symbol, 'synthetic': True, 'url': 'fixture://synthetic/' + symbol,
                'retrieved_at': stamp, 'fallback_attempts': [],
                'meta': {'symbol': symbol, 'currency': 'USD', 'exchangeName': 'NMS',
                         'instrumentType': 'ETF' if symbol in etfs else 'EQUITY',
                         'regularMarketTime': int(datetime(2026, 10, 22, 20, tzinfo=timezone.utc).timestamp())},
                'events': {'splits': {}, 'dividends': {}},
                'observations': [{'date': day, 'close': round(100 + i * slope, 4),
                                  'adj_close': round(100 + i * slope, 4),
                                  'volume': 2000000, 'missing': False} for i, day in enumerate(dates)]}

    def quote(symbol):
        return {'symbol': symbol, 'synthetic': True, 'url': 'fixture://synthetic/' + symbol,
                'retrieved_at': stamp, 'company_name': 'Synthetic ' + symbol,
                'exchange': 'NASDAQ-GS', 'sector': 'Synthetic', 'industry': 'Semiconductors',
                'market_cap_raw': '3,000,000,000', 'market_cap_usd': 3000000000,
                'timestamp_note': 'Manufactured fixture; no market observation.'}

    def holdings(theme):
        symbols = by_anchor.get(theme['anchor']) or ['NVDA', 'ADI']
        return {'synthetic': True, 'as_of': '2026-10-22', 'retrieved_at': stamp,
                'url': 'fixture://synthetic/holdings',
                'rows': [{'ticker': s, 'company': 'Synthetic ' + s, 'weight_pct': 100 / len(symbols)} for s in symbols]}

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / 'config').mkdir()
        for name, value in [('themes.json', registry), ('evidence_reviews.json', evidence),
                            ('anchor_comparisons.json', {'comparisons': []}),
                            ('sources.json', {'prices': {'interval_seconds': 0}, 'index_constituents': {}})]:
            (root / 'config' / name).write_text(json.dumps(value))
        with patch('src.themescope.collect.datetime', FixtureClock), \
             patch('src.themescope.collect.fetch_yahoo_chart', side_effect=chart), \
             patch('src.themescope.collect.fetch_nasdaq_summary', side_effect=quote), \
             patch('src.themescope.collect.fetch_holdings', side_effect=holdings), \
             patch('src.themescope.collect.fetch_sec_latest_annual', side_effect=AssertionError('No SEC requests in synthetic fixture')), \
             patch('src.themescope.v5.collect_inputs', return_value={}):
            snapshot, raw = build_snapshot(root, requested_asof='2026-10-22')
    snapshot['synthetic'] = raw['synthetic'] = True
    snapshot['sources'] = {'price_provider': 'Manufactured deterministic fixture', 'partial': False}
    snapshot['limitations'] = ['Synthetic legacy regression fixture; no actual market data or live research signals.']
    enrich(snapshot, raw)
    for name, value in [('latest_snapshot.json', snapshot), ('raw_inputs.json', raw)]:
        (destination / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))+'\n', encoding='utf-8')
    (destination / 'source_matrix.csv').write_text('source,status\nsynthetic_fixture,manufactured_no_network\n')
    return snapshot, raw


if __name__ == '__main__':
    generate(ROOT / 'tests/fixtures/v1')
