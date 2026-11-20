"""Offline, evidence-backed TradingView identifiers; never infer a venue prefix."""
def resolve(ticker: str, mapping: dict) -> str:
    record = mapping.get(ticker, {})
    if record.get('status') != 'verified' or not record.get('symbol'):
        raise ValueError(f'TradingView identifier unresolved: {ticker}: {record.get("reason", "evidence required")}')
    return record['symbol']
