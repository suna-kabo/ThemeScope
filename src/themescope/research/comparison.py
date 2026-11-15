"""Read-only five-session research comparison on today's reviewed member basket.

This recalculates cross-sectional metrics, not historical index/accounting state.
It never reads saved refreshes or persists a reconstructed prior snapshot.
"""
from hashlib import sha256
import json

from ..themes.calculations import benchmarks, breadth, calendar, deterministic, number, usable
from ..themes.index import ema
from .context import field


def membership_signature(members):
    values = sorted((member.ticker, str(member.role)) for member in members)
    return sha256(json.dumps(values).encode()).hexdigest()


def _population(metrics, horizon):
    return sorted(key for key, pair in metrics.items() if pair[horizon].value is not None)


def _matches_current(current, metrics, scores, target, methodology, signatures):
    if current.get('session') != target or current.get('methodology') != methodology:
        return False
    rows = {row['theme_id']: row for row in current.get('themes', ()) if row['status'] == 'active'}
    if rows.keys() != scores.keys():
        return False
    relationships = current.get('relationships', ())
    for key, signature in signatures.items():
        pairs = sorted((row['ticker'], str(row['role'])) for row in relationships
                       if row['theme_id'] == key and row['role'] in ('Core', 'Enabler'))
        if sha256(json.dumps(pairs).encode()).hexdigest() != signature:
            return False
    return all(number(rows[key].get('score')) == score and
               len(rows[key].get('returns') or ()) == len(metrics[key]) and
               all(number(field(value, 'value')) == expected.value
                   for value, expected in zip(rows[key]['returns'], metrics[key]))
               for key, score in scores.items())


@deterministic
def reconstruct(configuration, bars, sessions, target, *, members_for=None, current=None,
                change_sessions=5):
    """Return (prior research metrics or None, explicit comparison provenance).

    Freeze the current approved selection for BOTH dates. A Nov 16 addition can
    contribute its known historical prices without claiming Nov 9 membership.
    An explicit selection supports the separately approved launch-close preview.
    All percentile populations must agree globally across the two dates.
    """
    sessions = calendar(sessions)
    end = sessions.index(target)
    if type(change_sessions) is not int or change_sessions <= 0:
        raise ValueError('Positive completed-session comparison horizon required')
    select = members_for or (lambda key: configuration.members_on(key, target))
    members = {theme.theme_id: tuple(member for member in select(theme.theme_id)
                                    if member.calculation_eligible)
               for theme in configuration.themes if theme.status == 'active'}
    signatures = {key: membership_signature(rows) for key, rows in sorted(members.items())}
    provenance = dict(version='themescope-same-basis-comparison-1', available=False,
        reason='insufficient_completed_history', basis='current_reviewed_membership',
        basis_session=target, current_session=target, previous_session=None,
        change_sessions=change_sessions, methodology=configuration.methodology['version'],
        membership_hash=sha256(json.dumps(signatures, sort_keys=True).encode()).hexdigest(),
        official_history=False, horizon_populations={}, ranked_population=[])
    if end < change_sessions:
        return None, provenance
    previous_day = sessions[end-change_sessions]
    provenance['previous_session'] = previous_day
    if end-change_sessions < max(configuration.methodology['return_sessions']):
        return None, provenance
    frozen = lambda key: members.get(key, ())
    metrics, scores, _ = benchmarks(configuration, bars, sessions, target, members_for=frozen)
    old_metrics, old_scores, _ = benchmarks(configuration, bars, sessions, previous_day, members_for=frozen)
    if current is not None and not _matches_current(current, metrics, scores, target, configuration.methodology['version'], signatures):
        provenance['reason'] = 'current_basis_mismatch'
        return None, provenance
    for index, horizon in enumerate(configuration.methodology['return_sessions']):
        provenance['horizon_populations'][str(horizon)] = dict(
            current=_population(metrics, index), previous=_population(old_metrics, index))
    ranked = sorted(key for key, score in scores.items() if score is not None)
    old_ranked = sorted(key for key, score in old_scores.items() if score is not None)
    provenance['ranked_population'] = ranked
    if (ranked != old_ranked or any(row['current'] != row['previous']
                                   for row in provenance['horizon_populations'].values())):
        provenance['reason'] = 'ranked_universe_changed'
        return None, provenance
    if not ranked:
        provenance['reason'] = 'unavailable_score'
        return None, provenance
    symbols = sorted({member.ticker for rows in members.values() for member in rows})
    closes = {}; stock_emas = {}
    for symbol in symbols:
        prices = [row.adjusted_close if usable(row := bars.get((symbol, day))) else None
                  for day in sessions[:end-change_sessions+1]]
        closes[symbol] = prices[-1]
        stock_emas[symbol] = tuple(ema(prices, period) for period in configuration.methodology['ema_periods'])
    themes = []
    for theme in configuration.themes:
        names = [member.ticker for member in members.get(theme.theme_id, ())]
        row = dict(theme_id=theme.theme_id, status=theme.status, score=old_scores.get(theme.theme_id),
                   returns=old_metrics.get(theme.theme_id),
                   research_member_signature=signatures.get(theme.theme_id))
        row['breadth'] = tuple(breadth(names, closes, {name: stock_emas[name][index] for name in names}, configuration.methodology)
                               for index in (0, 1))
        themes.append(row)
    provenance.update(available=True, reason='comparable')
    return dict(session=previous_day, methodology=configuration.methodology['version'], themes=themes,
                comparison_basis='current_reviewed_membership', basis_session=target), provenance
