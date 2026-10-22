"""Dated display fields derived exclusively from the retrieved input series."""
import math
from .metrics import observation_map, trend_metric, return_metric


def enrich(snapshot, raw):
    session = snapshot.get('session_date')
    calendar = raw.get('session_calendar', [])
    def fields(symbol):
        chart = raw.get('charts', {}).get(symbol)
        if not chart or session not in calendar:
            return {'price_close': None, 'history': [], 'daily_change': None}
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
            'ema21_slope_5': trend.get('ema21_slope_5'),
            'history': [{'date': d, 'close': rows.get(d, {}).get('close')} for d in dates[-64:]],
        }
    for row in snapshot.get('context', []):
        row.update(fields(row['ticker']))
    for theme in snapshot.get('themes', []):
        theme.update(fields(theme['anchor']))
    return snapshot


def validate(snapshot, raw):
    """Publication gate: complete retrieval, aligned core metrics and a useful pool."""
    problems = []
    session = snapshot.get('session_date')
    if not session:
        problems.append('No completed market session was retrieved')
    mandatory = {'SPY', 'QQQ'} | {t.get('anchor') for t in snapshot.get('themes', [])}
    failures = raw.get('errors', {}).get('charts', {})
    if mandatory.intersection(failures) or mandatory.intersection(raw.get('errors', {}).get('holdings', {})):
        problems.append('Mandatory market/anchor retrieval failed; see source_errors in refresh_status.json')
    def valid_number(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
    rows = snapshot.get('context', []) + snapshot.get('themes', [])
    if not {'SPY', 'QQQ'}.issubset({r.get('ticker') for r in snapshot.get('context', [])}):
        problems.append('SPY and QQQ are required')
    if not snapshot.get('themes'):
        problems.append('No themes available')
    for row in rows:
        name = row.get('ticker') or row.get('anchor')
        if not valid_number(row.get('price_close')) or row['price_close'] <= 0:
            problems.append(f'{name}: closing price unavailable')
        for window in ('5', '21', '63'):
            metric = row.get('returns', {}).get(window, {})
            if metric.get('status') != 'valid' or not valid_number(metric.get('value')) or metric.get('session_date') != session:
                problems.append(f'{name}: {window}-session return unavailable or misaligned')
        chart = raw.get('charts', {}).get(name)
        if not chart or session not in raw.get('session_calendar', []):
            problems.append(f'{name}: underlying dated history missing')
        else:
            raw_price = observation_map(chart).get(session, {}).get('close')
            if raw_price != row.get('price_close'):
                problems.append(f'{name}: price does not match retrieved session')
            for window in (5, 21, 63):
                calculated = return_metric(chart, raw['session_calendar'], session, window)
                value = row.get('returns', {}).get(str(window), {}).get('value')
                if calculated.get('status') != 'valid' or not valid_number(value) or not math.isclose(calculated['value'], value, abs_tol=1e-10):
                    problems.append(f'{name}: return does not match retrieved observations')
    for market in snapshot.get('context', []):
        for field in ('daily_change', 'ema21_distance', 'ema50_distance'):
            if not valid_number(market.get(field)):
                problems.append(f"{market.get('ticker')}: {field} unavailable")
    spy = next((r for r in snapshot.get('context', []) if r.get('ticker') == 'SPY'), {})
    for theme in snapshot.get('themes', []):
        for window in ('21', '63'):
            benchmark = spy.get('returns', {}).get(window, {}).get('value')
            absolute = theme.get('returns', {}).get(window, {}).get('value')
            relative = theme.get('excess_returns', {}).get(window, {}).get('value')
            if not all(valid_number(v) for v in (benchmark, absolute, relative)) or not math.isclose(relative, absolute - benchmark, abs_tol=1e-10):
                problems.append(f"{theme.get('anchor')}: excess return unavailable or inconsistent")
    for theme in snapshot.get('themes', []):
        for stock in theme.get('selected', []):
            if stock.get('session_date') != session:
                problems.append(f"{stock.get('ticker')}: selected stock date is misaligned")

    if problems:
        raise ValueError('; '.join(problems))
