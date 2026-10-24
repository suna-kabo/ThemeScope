#!/usr/bin/env python3
"""Seed the persistent v7 cache from an existing self-contained run bundle."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import zipfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.themescope.price_cache import PriceCache


def _charts_from_sidecar(content: bytes) -> dict:
    output = {}
    with gzip.GzipFile(fileobj=io.BytesIO(content), mode='rb') as compressed:
        with io.TextIOWrapper(compressed, encoding='utf-8', newline='') as handle:
            for row in csv.DictReader(handle):
                output[row['symbol']] = json.loads(row['chart_json'])
    return output


def _load_run(path: Path) -> tuple[dict, dict[str, bytes]]:
    if path.is_file():
        with zipfile.ZipFile(path) as archive:
            raw = json.loads(archive.read('raw_inputs.json').decode('utf-8'))
            sidecars = {name: archive.read(name) for name in archive.namelist() if name.endswith('.csv.gz') and 'price' in name}
            return raw, sidecars
    raw = json.loads((path / 'raw_inputs.json').read_text(encoding='utf-8'))
    sidecars = {item.name: item.read_bytes() for item in path.glob('*prices.csv.gz')}
    return raw, sidecars


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('output'), help='Existing run directory or run_bundle.zip')
    args = parser.parse_args()
    raw, sidecars = _load_run(args.input)
    root = ROOT
    cache = PriceCache(root / 'cache')
    charts = dict(raw.get('charts', {}))
    charts.update(raw.get('v5', {}).get('charts', {}))
    charts.update(raw.get('v5', {}).get('iwm_breadth_charts', {}))
    for name, content in sidecars.items():
        charts.update(_charts_from_sidecar(content))
    seeded = 0
    skipped = 0
    for symbol, chart in charts.items():
        old = cache.read(symbol)
        if old and old['latest_completed_session'] >= max(row['date'] for row in chart.get('observations', [])):
            skipped += 1
            continue
        merged = cache._merge(old.get('chart') if old else None, chart, symbol)
        refresh = old.get('full_refresh_at') if old else chart.get('retrieved_at')
        cache.write(symbol, merged, full_refresh_at=refresh)
        seeded += 1
    caps = {}
    for symbol, quote in raw.get('quotes', {}).items():
        if isinstance(quote, dict) and quote.get('market_cap_usd') is not None:
            caps[symbol.upper()] = {'market_cap_usd': quote.get('market_cap_usd'), 'retrieved_at': quote.get('retrieved_at'), 'source': 'Nasdaq quote summary (legacy run cache)'}
    cap_path = root / 'cache' / 'market_cap.json'
    cap_path.parent.mkdir(parents=True, exist_ok=True)
    cap_path.write_text(json.dumps({'version': 1, 'source': 'seeded from prior run; no refresh performed', 'symbols': caps}, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    universes = raw.get('v5', {}).get('index_universes', {})
    universes.update(raw.get('context_holdings', {}))
    for name in ('SPY', 'QQQ', 'IWM'):
        if name in universes:
            cache.save_universe(name, universes[name])
    print(f'Seeded {seeded:,} price histories; kept {skipped:,} newer cache entries; loaded {len(caps):,} maintained market-cap facts; no network requests.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
