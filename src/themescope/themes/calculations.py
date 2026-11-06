"""Pure vNext price/median/LOO calculations. Returns are fractions, scores 0..100.

The caller supplies the authoritative completed US-session calendar. Missing bars
never compress that calendar. No provider access or legacy ETF inputs live here.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext, Context, ROUND_HALF_EVEN
from functools import wraps
from pathlib import Path
import json
from ..domain import iso_date

D = Decimal


def deterministic(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with localcontext(Context(prec=34, rounding=ROUND_HALF_EVEN)):
            return function(*args, **kwargs)
    return wrapped


def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = D(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


# One versioned policy source; callers may pass another explicitly versioned policy.
POLICY = json.loads((Path(__file__).resolve().parents[3] / 'config/vnext/methodology.json').resolve().read_text())


def calendar(sessions):
    sessions = tuple(sessions)
    if not sessions or sessions != tuple(sorted(set(sessions))) or any(not iso_date(s) for s in sessions):
        raise ValueError('Ordered unique ISO trading sessions required')
    return sessions


@dataclass(frozen=True)
class Bar:
    ticker: str
    session: str
    adjusted_close: Decimal
    close: Decimal
    volume: Decimal
    adjustment: str = 'split,spin-off'
    currency: str = 'USD'
    completed: bool = True
    regular_session: bool = True

    def __post_init__(self):
        if not self.ticker or self.ticker != self.ticker.upper() or not iso_date(self.session):
            raise ValueError('Bar requires uppercase ticker and session')
        for field in ('adjusted_close', 'close', 'volume'):
            value = number(getattr(self, field))
            if value is None or value < 0 or (field != 'volume' and value == 0):
                raise ValueError('Invalid bar ' + field)
            object.__setattr__(self, field, value)
        if self.adjustment != POLICY['adjustment'] or self.currency != 'USD':
            raise ValueError('Only split/spin-off price adjustment and USD are supported')


def bar_map(bars):
    result = {}
    for bar in bars:
        key = (bar.ticker, bar.session)
        if key in result:
            raise ValueError('Duplicate symbol/session bar')
        result[key] = bar
    return result


def usable(bar):
    return bar is not None and bar.completed and bar.regular_session


@deterministic
def price_return(bars, ticker, sessions, target, horizon):
    sessions = calendar(sessions)
    if horizon <= 0:
        raise ValueError('Positive return horizon required')
    index = sessions.index(target)
    if index < horizon:
        return None
    first, last = bars.get((ticker, sessions[index-horizon])), bars.get((ticker, target))
    if not usable(first) or not usable(last):
        return None
    return last.adjusted_close / first.adjusted_close - 1


@deterministic
def median(values):
    values = sorted(values)
    if not values:
        return None
    half = len(values)//2
    return values[half] if len(values) % 2 else (values[half-1] + values[half])/2


@dataclass(frozen=True)
class Metric:
    value: Decimal | None
    valid: int
    configured: int
    coverage: Decimal


def unique_symbols(symbols):
    symbols = tuple(symbols)
    if len(set(symbols)) != len(symbols):
        raise ValueError('Duplicate configured symbol')
    return tuple(sorted(symbols))


@deterministic
def aggregate(symbols, values, *, minimum=None, policy=POLICY):
    symbols = unique_symbols(symbols)
    valid = [v for s in symbols if (v := number(values.get(s))) is not None]
    coverage = D(len(valid))/len(symbols) if symbols else D(0)
    minimum = policy['theme_minimum'] if minimum is None else minimum
    value = median(valid) if len(valid) >= minimum and coverage >= D(str(policy['coverage'])) else None
    return Metric(value, len(valid), len(symbols), coverage)


@deterministic
def percentiles(values):
    valid = sorted((v, key) for key, value in values.items() if (v := number(value)) is not None)
    result = dict.fromkeys(values)
    if len(valid) < 2:
        return result
    start = 0
    while start < len(valid):
        end = start + 1
        while end < len(valid) and valid[end][0] == valid[start][0]:
            end += 1
        percentile = (D(start + 1 + end)/2 - 1)/(len(valid)-1)*100
        for _, key in valid[start:end]:
            result[key] = percentile
        start = end
    return result


@deterministic
def theme_scores(metrics, policy=POLICY):
    """Each horizon ranks its available Active themes; score requires both."""
    p1 = percentiles({key: pair[0].value for key, pair in metrics.items()})
    p3 = percentiles({key: pair[1].value for key, pair in metrics.items()})
    a, b = map(lambda x: D(str(x)), policy['weights'])
    return {key: a*p1[key]+b*p3[key] if p1[key] is not None and p3[key] is not None else None for key in metrics}


@dataclass(frozen=True)
class Relative:
    peer1: Metric
    peer3: Metric
    er1: Decimal | None
    er3: Decimal | None
    w: Decimal | None


@deterministic
def relative(ticker, symbols, returns1, returns3, policy=POLICY):
    symbols = unique_symbols(symbols)
    if ticker not in symbols:
        raise ValueError('Stock must belong to configured theme')
    peers = tuple(s for s in symbols if s != ticker)
    p1 = aggregate(peers, returns1, minimum=policy['peer_minimum'], policy=policy)
    p3 = aggregate(peers, returns3, minimum=policy['peer_minimum'], policy=policy)
    s1, s3 = number(returns1.get(ticker)), number(returns3.get(ticker))
    er1 = s1-p1.value if s1 is not None and p1.value is not None else None
    er3 = s3-p3.value if s3 is not None and p3.value is not None else None
    a, b = map(lambda x: D(str(x)), policy['weights'])
    w = a*er1+b*er3 if er1 is not None and er3 is not None else None
    return Relative(p1, p3, er1, er3, w)


@deterministic
def breadth(symbols, closes, emas, policy=POLICY):
    values = {s: D(number(closes[s]) > number(emas[s])) for s in symbols
              if number(closes.get(s)) is not None and number(emas.get(s)) is not None}
    coverage = aggregate(symbols, values, policy=policy)
    value = sum(values.values())/len(values)*100 if coverage.value is not None else None
    return Metric(value, coverage.valid, coverage.configured, coverage.coverage)


def benchmarks(configuration, bars, sessions, target, *, members_for=None):
    """Same formulas for effective membership or an explicit research selection."""
    members_for=members_for or (lambda theme_id: configuration.members_on(theme_id,target))
    symbols = sorted({m.ticker for t in configuration.themes for m in members_for(t.theme_id)})
    returns = [{s: price_return(bars, s, sessions, target, n) for s in symbols}
               for n in configuration.methodology['return_sessions']]
    metrics = {t.theme_id: tuple(aggregate([m.ticker for m in members_for(t.theme_id)], r,
                                          policy=configuration.methodology) for r in returns)
               for t in configuration.themes if t.status == 'active'}
    return metrics, theme_scores(metrics, configuration.methodology), returns
