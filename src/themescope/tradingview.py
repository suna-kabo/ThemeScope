"""Offline, evidence-backed TradingView identifiers; never infer a venue prefix."""
import json
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


def heading(theme: dict) -> str:
    return '###' + theme['name'].replace(',', ' ') + ' (' + theme['anchor'] + ')'
