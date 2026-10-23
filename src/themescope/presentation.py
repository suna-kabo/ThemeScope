"""Dated display fields derived exclusively from the retrieved input series."""
import math
from datetime import datetime
from zoneinfo import ZoneInfo
from .metrics import observation_map, trend_metric, return_metric


def _hkt_display(value):
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(str(value).replace('Z', '+00:00')).astimezone(ZoneInfo('Asia/Hong_Kong'))
    except (TypeError, ValueError):
        return None
    return stamp.strftime('%d %b %Y, %I:%M %p HKT').lstrip('0')


def enrich(snapshot, raw):
    session = snapshot.get('session_date')
    calendar = raw.get('session_calendar', [])
    def fields(symbol):
        chart = raw.get('charts', {}).get(symbol)
        if not chart or session not in calendar:
            return {'price_close': None, 'history': [], 'daily_change': None,
                    'price_status': 'unavailable',
                    'price_reason': raw.get('errors', {}).get('charts', {}).get(symbol, 'Price history unavailable')}
        rows = observation_map(chart)
        dates = calendar[:calendar.index(session) + 1]
        current = rows.get(session, {}).get('close')
        previous = rows.get(dates[-2], {}).get('close') if len(dates) > 1 else None
        trend = trend_metric(chart, calendar, session, snapshot['settings'])
        # Yahoo close is split-adjusted, unlike adj_close which includes distributions.
        return {
            'price_close': current,
            'daily_change': current / previous - 1 if current and previous else None,
            'ema21_distance': current / trend['ema21'] - 1 if current and trend.get('ema21') else None,
            'ema50_distance': current / trend['ema50'] - 1 if current and trend.get('ema50') else None,
            'ema21': trend.get('ema21'), 'ema50': trend.get('ema50'),
            'above_ema21': current > trend['ema21'] if current is not None and trend.get('ema21') is not None else None,
            'above_ema50': current > trend['ema50'] if current is not None and trend.get('ema50') is not None else None,
            'price_status': 'valid' if current is not None else 'unavailable',
            'price_reason': None if current is not None else f'No close observation for {session}',
            'price_session_date': session,
            'price_source_url': chart.get('url'),
            'price_retrieved_at': chart.get('retrieved_at'),
            'ema21_slope_5': trend.get('ema21_slope_5'),
            'history': [{'date': d, 'close': rows.get(d, {}).get('close')} for d in dates[-64:]],
        }
    for row in snapshot.get('context', []):
        row.update(fields(row['ticker']))
        row['instrument_type'] = 'equity_market_etf'
        row['price_retrieved_at_hkt_display'] = _hkt_display(row.get('price_retrieved_at'))
    for theme in snapshot.get('themes', []):
        theme.update(fields(theme['anchor']))
    for item in snapshot.get('volatility_context', []):
        ticker = item.get('ticker')
        chart = raw.get('charts', {}).get(ticker)
        rows = observation_map(chart) if chart else {}
        dates = [d for d in calendar if d <= session and d in rows and isinstance(rows[d].get('close'), (int, float))] if session else []
        current_date = dates[-1] if dates else None
        current = rows.get(current_date, {}).get('close') if current_date else None
        previous = rows.get(dates[-2], {}).get('close') if len(dates) > 1 else None
        item.update({
            'instrument_type': 'volatility_index',
            'level': current,
            'daily_change': current / previous - 1 if current is not None and previous not in (None, 0) else None,
            'return5': current / rows[dates[-6]]['close'] - 1 if current is not None and len(dates) >= 6 and rows[dates[-6]].get('close') not in (None, 0) else None,
            'return21': current / rows[dates[-22]]['close'] - 1 if current is not None and len(dates) >= 22 and rows[dates[-22]].get('close') not in (None, 0) else None,
            'trailing_1y_percentile': (100 * sum(rows[d]['close'] <= current for d in dates[-252:]) / len(dates[-252:])) if current is not None and len(dates) >= 252 else None,
            'trailing_1y_observations': min(len(dates), 252),
            'observation_date': current_date,
            'source_url': (chart or {}).get('url'),
            'retrieved_at': (chart or {}).get('retrieved_at'),
            'retrieved_at_hkt_display': _hkt_display((chart or {}).get('retrieved_at')),
            'source_status': 'available' if current is not None else 'unavailable',
            'source_reason': None if current is not None else raw.get('errors', {}).get('charts', {}).get(ticker, 'No VIX close observation available'),
        })
    return snapshot


def validate(snapshot, raw):
    """Publication gate for required market facts and internally consistent values."""
    problems = []
    session = snapshot.get('session_date')
    if not session:
        problems.append('No completed market session was retrieved')
    failures = raw.get('errors', {}).get('charts', {})
    if {'SPY', 'QQQ'}.intersection(failures):
        problems.append('Required SPY/QQQ price retrieval failed; see source_errors in refresh_status.json')
    def valid_number(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
    rows = snapshot.get('context', []) + snapshot.get('themes', [])
    context_by_ticker = {r.get('ticker'): r for r in snapshot.get('context', [])}
    if not {'SPY', 'QQQ', 'IWM'}.issubset(context_by_ticker):
        problems.append('SPY, QQQ, and IWM context records are required, even when a source is unavailable')
    for row in rows:
        name = row.get('ticker') or row.get('anchor')
        is_iwm_context = name == 'IWM' and any(row is candidate for candidate in snapshot.get('context', []))
        if not is_iwm_context and (not valid_number(row.get('price_close')) or row['price_close'] <= 0):
            problems.append(f'{name}: closing price unavailable')
        required_windows = ('5', '21', '63') if name in {'SPY', 'QQQ'} or (name == 'IWM' and valid_number(row.get('price_close'))) else ()
        for window in required_windows:
            metric = row.get('returns', {}).get(window, {})
            if metric.get('status') != 'valid' or not valid_number(metric.get('value')) or metric.get('session_date') != session:
                problems.append(f'{name}: {window}-session return unavailable or misaligned')
        chart = raw.get('charts', {}).get(name)
        if chart and session in raw.get('session_calendar', []):
            raw_price = observation_map(chart).get(session, {}).get('close')
            if raw_price != row.get('price_close'):
                problems.append(f'{name}: price does not match retrieved session')
            for window in (5, 21, 63):
                calculated = return_metric(chart, raw['session_calendar'], session, window)
                value = row.get('returns', {}).get(str(window), {}).get('value')
                if calculated.get('status') != 'valid' or not valid_number(value) or not math.isclose(calculated['value'], value, abs_tol=1e-10):
                    problems.append(f'{name}: return does not match retrieved observations')
        elif not is_iwm_context:
            problems.append(f'{name}: underlying dated history missing')
    for market in snapshot.get('context', []):
        if market.get('ticker') == 'IWM' and not valid_number(market.get('price_close')):
            continue
        for field in ('daily_change', 'ema21_distance', 'ema50_distance'):
            if not valid_number(market.get(field)):
                problems.append(f"{market.get('ticker')}: {field} unavailable")
    spy = next((r for r in snapshot.get('context', []) if r.get('ticker') == 'SPY'), {})
    for theme in snapshot.get('themes', []):
        for window in ('21', '63'):
            benchmark = spy.get('returns', {}).get(window, {}).get('value')
            absolute = theme.get('returns', {}).get(window, {}).get('value')
            relative = theme.get('excess_returns', {}).get(window, {}).get('value')
            if all(valid_number(v) for v in (benchmark, absolute, relative)) and not math.isclose(relative, absolute - benchmark, abs_tol=1e-10):
                problems.append(f"{theme.get('anchor')}: excess return unavailable or inconsistent")
    for theme in snapshot.get('themes', []):
        if theme.get('session_date') not in (None, session):
            problems.append(f"{theme.get('anchor')}: anchor metric date is misaligned")

    for item in snapshot.get('volatility_context', []):
        if item.get('level') is not None and not valid_number(item.get('level')):
            problems.append(f"{item.get('ticker')}: volatility level is invalid")
        if item.get('instrument_type') != 'volatility_index':
            problems.append(f"{item.get('ticker')}: volatility record has an invalid instrument type")
        if any(key in item for key in ('index_breadth', 'holdings_breadth', 'breadth21', 'breadth50')):
            problems.append(f"{item.get('ticker')}: volatility record must not contain breadth fields")

    if problems:
        raise ValueError('; '.join(problems))
