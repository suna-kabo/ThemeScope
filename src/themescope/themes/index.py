"""Chain-linked, drifting price index; explicit membership/indicator-only bootstrap.

A point's weights are holdings AFTER that close's rebalance. earned_symbols names
holdings that earned the return ending at the point. No live launch is inferred.
"""
from dataclasses import dataclass, replace
from decimal import Decimal as D
from .calculations import POLICY, calendar, deterministic, number, unique_symbols, usable


class IndexUnavailable(ValueError):
    pass


@dataclass(frozen=True)
class IndexPoint:
    session: str
    level: D
    weights: tuple[tuple[str, D], ...]
    earned_symbols: tuple[str, ...]
    rebalanced: bool
    bootstrap: bool


def adjusted(bars, ticker, session):
    value = bars.get((ticker, session))
    if not usable(value):
        raise IndexUnavailable('Missing completed index price: '+ticker+' '+session)
    return value.adjusted_close


@deterministic
def build_index(configuration, theme_id, bars, sessions, start, target, *,
                bootstrap_symbols=None, formal_rebalances=(), terminal_values=()):
    """Initialize at explicit start close, then earn subsequent sessions only.

    Bootstrap symbols must be supplied explicitly for a synthetic indicator seed.
    Live membership always comes from effective configuration, never that override.
    This pure function calculates research fixtures; it does not activate production.
    """
    sessions = calendar(sessions)
    begin, end = sessions.index(start), sessions.index(target)
    if end < begin or end+1 >= len(sessions):
        raise ValueError('Index requires ordered range plus next trading session')
    theme = next(t for t in configuration.themes if t.theme_id == theme_id)
    if theme.status != 'active':
        raise IndexUnavailable('Only Active themes have a synthetic index')
    formal_rebalances = set(formal_rebalances)
    if any(s not in sessions for s in formal_rebalances):
        raise ValueError('Rebalance must occur at a configured session close')
    bootstrap = bootstrap_symbols is not None
    from ..corporate_actions import TerminalValue, resolve_values
    if any(not isinstance(v,TerminalValue) for v in terminal_values):
        raise ValueError('Typed, approved terminal accounting required')
    relevant={m.ticker for m in configuration.memberships if m.theme_id==theme_id}
    selected=tuple(v for v in terminal_values if v.ticker in relevant)
    terminal={(v.ticker,v.valuation_session):v for v in selected}
    if selected:
        actions=tuple(a for a in configuration.corporate_actions if a.ticker in relevant and a.valuation_session<=target)
        expected={(v.ticker,v.valuation_session):v for v in resolve_values(actions,bars,target)}
        if len(terminal)!=len(selected) or terminal!=expected:
            raise ValueError('Terminal accounting differs from approved terms and prices')
    if bootstrap and terminal:
        raise ValueError('Terminal accounting is not a bootstrap trading price')
    symbols = unique_symbols(bootstrap_symbols) if bootstrap else None
    minimum = configuration.methodology['theme_minimum']

    def members(earned_session):
        names = symbols if bootstrap else unique_symbols(m.ticker for m in configuration.members_on(theme_id, earned_session))
        if len(names) < minimum:
            raise IndexUnavailable('Fewer than minimum effective Core/Enabler members')
        return names

    held = members(sessions[begin+1])
    for ticker in held:
        adjusted(bars, ticker, start)
    weights = {ticker: D(1)/len(held) for ticker in held}
    level = D(str(configuration.methodology['initial_index_level']))
    points = [IndexPoint(start, level, tuple(sorted(weights.items())), (), True, bootstrap)]
    for i in range(begin+1, end+1):
        session, previous = sessions[i], sessions[i-1]
        earned = tuple(sorted(weights))
        if earned != members(session):
            raise ValueError('Holdings and earned-session membership disagree')
        def factor(ticker):
            value=terminal.get((ticker,session))
            if value is not None:
                if previous!=value.last_trading_session or (ticker,session) in bars:
                    raise IndexUnavailable('Invalid terminal holding boundary: '+ticker)
                return value.value/value.previous_raw_close
            return adjusted(bars,ticker,session)/adjusted(bars,ticker,previous)
        grown = {ticker: weight*factor(ticker) for ticker, weight in weights.items()}
        growth = sum(grown.values())
        level *= growth
        weights = {ticker: value/growth for ticker,value in grown.items()}
        following = members(sessions[i+1])
        rebalance = following != earned or session in formal_rebalances
        if rebalance:
            for ticker in following:
                adjusted(bars,ticker,session)
            weights = {ticker: D(1)/len(following) for ticker in following}
        points.append(IndexPoint(session,level,tuple(sorted(weights.items())),earned,rebalance,bootstrap))
    return tuple(points)


@deterministic
def ema(values, period):
    if period < 1:
        raise ValueError('Positive EMA period required')
    clean = [number(v) for v in values]
    if len(clean) < period or any(v is None or v <= 0 for v in clean):
        return None
    value = sum(clean[:period])/period
    alpha = D(2)/(period+1)
    for close in clean[period:]:
        value = alpha*close+(1-alpha)*value
    return value


def trend(close, ema21, ema50):
    close, ema21, ema50 = map(number,(close,ema21,ema50))
    if any(v is None or v <= 0 for v in (close,ema21,ema50)):
        return 'Unavailable'
    if close > ema21 and close > ema50:
        return 'Bullish'
    if close < ema21 and close < ema50:
        return 'Bearish'
    return 'Mixed'


@deterministic
def indicators(points, sessions, *, bootstrap=(), policy=POLICY):
    """Scale the indicator-only seed to the live initialization close (normally 100).

    Bootstrap must end exactly at live initialization, and is never returned as
    live signal history. No calendar gaps or mixed modes are silently accepted.
    """
    sessions = calendar(sessions)
    points, bootstrap = tuple(points), tuple(bootstrap)
    if not points:
        return ()
    combined = points
    if bootstrap:
        if any(not p.bootstrap for p in bootstrap) or any(p.bootstrap for p in points):
            raise ValueError('Explicit bootstrap seed and live points required')
        if bootstrap[-1].session != points[0].session:
            raise ValueError('Bootstrap must terminate at live initialization')
        scale = points[0].level/bootstrap[-1].level
        combined = tuple(replace(p,level=p.level*scale) for p in bootstrap[:-1])+points
    indices = [sessions.index(p.session) for p in combined]
    if indices != list(range(indices[0],indices[-1]+1)):
        raise ValueError('Indicator history must be contiguous trading sessions')
    result=[]
    offset=len(combined)-len(points)
    for i,point in enumerate(points,offset):
        values=[p.level for p in combined[:i+1]]
        short,long=(ema(values,n) for n in policy['ema_periods'])
        result.append({'session':point.session,'level':point.level,'ema21':short,'ema50':long,
                       'trend':trend(point.level,short,long),'bootstrap':point.bootstrap})
    return tuple(result)
