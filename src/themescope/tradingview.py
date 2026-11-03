"""Offline, evidence-backed TradingView identifiers; never infer a venue prefix."""
import json
import hashlib
import re
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import quote


def load_mapping(root: Path) -> dict:
    return json.loads((root / 'config/tradingview_symbols.json').read_text())['symbols']


def resolve(ticker: str, mapping: dict) -> str:
    record = mapping.get(ticker, {})
    if record.get('status') != 'verified' or not record.get('symbol'):
        raise ValueError(f'TradingView identifier unresolved: {ticker}: {record.get("reason", "evidence required")}')
    return record['symbol']


def attach(snapshot: dict, mapping: dict) -> None:
    for theme in snapshot['themes']:
        for row, ticker in [(theme, theme['anchor'])] + [(s, s['ticker']) for s in theme.get('selected', [])]:
            row['tradingview_symbol'] = resolve(ticker, mapping)
            row['chart_url'] = 'https://www.tradingview.com/chart/?symbol=' + quote(row['tradingview_symbol'], safe='')
    for row in snapshot['context']:
        row['tradingview_symbol'] = resolve(row['ticker'], mapping)
        row['chart_url'] = 'https://www.tradingview.com/chart/?symbol=' + quote(row['tradingview_symbol'], safe='')


def theme_symbols(theme: dict) -> list[str]:
    stocks = theme.get('selected', [])
    if len(stocks) > 20:
        raise ValueError(f'{theme["id"]}: more than 20 configured stocks')
    rows = [theme] + stocks
    for row in rows:
        if not row.get('tradingview_symbol'):
            raise ValueError(f'TradingView identifier unresolved: {row.get("ticker", row.get("anchor"))}')
    return [row['tradingview_symbol'] for row in rows]


def individual_filenames(themes: list[dict]) -> dict[str, str]:
    """Portable ETF-first names, independent of input order and case collisions."""
    def safe(value, fallback):
        value = unicodedata.normalize('NFKD', str(value)).encode('ascii', 'ignore').decode()
        return re.sub(r'[^A-Za-z0-9.-]+', '_', value).strip('_.-')[:100] or fallback

    if len({t['id'] for t in themes}) != len(themes):
        raise ValueError('Duplicate theme identity in individual exports')
    bases = {t['id']: safe(t['anchor'], 'ETF') + '_' + safe(t['name'], 'Theme') for t in themes}
    counts = Counter(base.casefold() for base in bases.values())
    result, used = {}, set()
    for theme_id in sorted(bases):
        base = bases[theme_id]
        suffix = '_' + hashlib.sha256(theme_id.encode()).hexdigest()[:12] if counts[base.casefold()] > 1 else ''
        name = base + suffix + '.txt'
        index = 1
        while name.casefold() in used:
            name = base + suffix + '_' + str(index) + '.txt'
            index += 1
        used.add(name.casefold())
        result[theme_id] = name
    return result


def section_heading(theme):
    """TradingView section token, separate from exchange-prefixed instruments."""
    label=re.sub(r'[,\r\n]+',' ',str(theme['anchor'])+' — '+str(theme['name']))
    return '###'+re.sub(r'\s+',' ',label).strip()
