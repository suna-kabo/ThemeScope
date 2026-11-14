"""Versioned research selection; never rewrites accounting or theme calculations."""
from copy import deepcopy
from decimal import Decimal as D
from hashlib import sha256
from pathlib import Path
import json

from ..themes.calculations import calendar, deterministic, number, usable
from .context import canonical_ranks, field
from .exports import Qualification, exports
from .primary import side

RULES_PATH = Path(__file__).resolve().parents[3] / 'config/vnext/research_v2.json'


def policy():
    return json.loads(RULES_PATH.read_text(encoding='utf-8'))


@deterministic
def liquidity(bars, ticker, sessions, target, rules):
    sessions = calendar(sessions)
    end = sessions.index(target)
    count = rules['liquidity_sessions']
    rows = [bars.get((ticker, day)) for day in sessions[max(0, end-count+1):end+1]]
    if len(rows) != count or any(not usable(row) for row in rows):
        return dict(available=False, eligible=False, close=None, average_volume=None,
                    turnover=None, average_dollar_volume=None, reasons=['missing_completed_regular_session'])
    close = rows[-1].close
    average = sum(row.close * row.volume for row in rows) / count
    reasons = []
    if close <= D(str(rules['price_floor_exclusive'])):
        reasons.append('price_not_above_floor')
    if average < D(str(rules['average_dollar_volume_floor'])):
        reasons.append('average_dollar_volume_below_floor')
    return dict(available=True, eligible=not reasons, close=close,
                average_volume=sum(row.volume for row in rows)/count,
                turnover=close*rows[-1].volume, average_dollar_volume=average, reasons=reasons)


@deterministic
def state(score, change, direction, rules):
    score, change = number(score), number(change)
    if score is None or not 0 <= score <= 100:
        return 'Unavailable'
    strength = score if direction == 'long' else 100-score
    delta = change if direction == 'long' or change is None else -change
    if strength >= D(str(rules['structural_boundary'])):
        return 'Fading' if delta is not None and delta <= -D(str(rules['material_score_change'])) else 'Leading'
    return 'Improving' if delta is not None and delta >= D(str(rules['material_score_change'])) else 'Lagging'


def state_reason(label, comparable):
    reasons = {'Leading': 'Structurally strong without a material recent decline',
               'Fading': 'Structurally strong, but strength declined over five sessions',
               'Improving': 'Strength improved materially over five sessions, below the structural boundary',
               'Lagging': 'Structurally weak without meaningful recent improvement',
               'Unavailable': 'Structural strength is unavailable'}
    result = reasons.get(label, 'Market direction is neutral')
    if not comparable and label in ('Leading', 'Lagging'):
        result = ('Structurally strong' if label == 'Leading' else 'Structurally weak') + '; five-session comparison unavailable'
    return result


@deterministic
def recent_change(snapshot, previous, sessions, rules):
    """Exact five-session comparison; no stale fallback or mixed membership basis."""
    empty = dict(available=False, session=None, score_change=None, rank_change=None,
                 breadth_change=None, reason='insufficient_comparable_history')
    end = sessions.index(snapshot['session'])
    horizon = rules['change_sessions']
    if end < horizon or not previous or previous.get('session') != sessions[end-horizon]:
        return {}, empty
    current = {t['theme_id']: t for t in snapshot['themes'] if t['status'] == 'active'}
    old = {t['theme_id']: t for t in previous.get('themes', ()) if t['status'] == 'active'}
    if snapshot['methodology'] != previous.get('methodology') or current.keys() != old.keys():
        return {}, dict(empty, reason='methodology_or_universe_changed')
    signatures_match = all(t.get('research_member_signature') and t['research_member_signature'] == old[k].get('research_member_signature')
                           for k,t in current.items())
    configuration_match = bool(snapshot.get('configuration_hash') and snapshot['configuration_hash'] == previous.get('configuration_hash'))
    legacy_comparison = not any(t.get('research_member_signature') for t in old.values())
    if not signatures_match and not (legacy_comparison and configuration_match):
        return {}, dict(empty, reason='membership_comparison_unavailable')
    ranks, prior_ranks = canonical_ranks(snapshot['themes']), canonical_ranks(previous['themes'])
    def horizon_population(rows, horizon):
        return {key for key,theme in rows.items() if len(theme.get('returns') or ())>horizon
                and number(field(theme['returns'][horizon], 'value')) is not None}
    if (ranks.keys() != prior_ranks.keys() or any(horizon_population(current, i) != horizon_population(old, i)
                                                for i in (0,1))):
        return {}, dict(empty, reason='ranked_universe_changed')
    result = {}
    for key, theme in current.items():
        before = old[key]
        same_members = (theme.get('research_member_signature') is not None and
                        theme.get('research_member_signature') == before.get('research_member_signature'))
        if not before.get('research_member_signature'):
            same_members = bool(snapshot.get('configuration_hash') and
                                snapshot['configuration_hash'] == previous.get('configuration_hash'))
        a_history, b_history = theme.get('history', {}), before.get('history', {})
        if (not a_history.get('series_id') or a_history.get('series_id') != b_history.get('series_id') or
                a_history.get('bootstrap') != b_history.get('bootstrap')):
            same_members = False
        if not same_members:
            result[key] = dict(empty, reason='membership_comparison_unavailable')
            continue
        score, prior = number(theme.get('score')), number(before.get('score'))
        if score is None or prior is None:
            result[key] = dict(empty, reason='unavailable_score')
            continue
        a = number(field(theme.get('breadth', [{}])[0], 'value'))
        b = number(field(before.get('breadth', [{}])[0], 'value'))
        result[key] = dict(available=True, session=previous['session'], score_change=score-prior,
                           rank_change=prior_ranks[key]-ranks[key] if ranks.keys() == prior_ranks.keys() else None,
                           breadth_change=a-b if a is not None and b is not None else None, reason='comparable')
    return result, empty


@deterministic
def attach(snapshot, bars, sessions, mapping, *, previous=None, previous_day=None, rules=None, related=()):
    rules = rules or policy()
    result = deepcopy(snapshot)
    sessions = calendar(sessions)
    themes = {t['theme_id']: t for t in result['themes']}
    relationships = result['relationships']
    for member in related:
        if (member.role != 'Related' or member.theme_id not in themes or
                themes[member.theme_id]['status'] != 'active' or result.get('production_blockers') or
                not member.active_on(result['session'])):
            continue
        if any(r['ticker']==member.ticker and r['theme_id']==member.theme_id for r in relationships):
            continue
        metric=dict(value=None, valid=0, configured=0, coverage=None)
        relationships.append(dict(ticker=member.ticker,theme_id=member.theme_id,role=member.role,
            relative=dict(w=None,er1=None,er3=None,peer1=dict(metric),peer3=dict(metric))))
    for key, theme in themes.items():
        members = sorted((r['ticker'], str(r['role'])) for r in relationships
                         if r['theme_id'] == key and r['role'] in ('Core','Enabler'))
        theme['research_member_signature'] = sha256(json.dumps(members).encode()).hexdigest()
    changes, unavailable = recent_change(result, previous, sessions, rules)
    ranks = canonical_ranks(result['themes'])
    direction = side(result.get('market_direction'))
    output = {}
    for key, theme in themes.items():
        change = changes.get(key, unavailable)
        score = theme.get('score') if theme['status'] == 'active' else None
        long_state = state(score, change['score_change'], 'long', rules)
        short_state = state(score, change['score_change'], 'short', rules)
        selected = long_state if direction == 'long' else short_state if direction == 'short' else None
        breadth = theme.get('breadth', ())
        sample = breadth[0] if breadth else {}
        percent, total = number(field(sample, 'value')), field(sample, 'valid', 0)
        above = (theme.get('breadth_above') or [None])[0]
        if above is None and percent is not None:
            above = (percent*D(str(total))/100).to_integral_value()
        if percent is None and above is not None and total:
            percent = D(above)/D(total)*100
        output[key] = dict(state=long_state, short_state=short_state, structural_score=score,
                           recent=dict(change), rank=ranks.get(key), side=direction,
                           researchable=selected in ('Leading', 'Improving', 'Fading'),
                           reason=state_reason(selected, change['available']),
                           breadth=dict(above=above,
                                        total=total, percent=percent,
                                        small_sample=total < rules['breadth_small_sample']))
    state_order = {name: i for i, name in enumerate(rules['state_order'])}
    def theme_key(key):
        row = output[key]
        label = row['state'] if direction != 'short' else row['short_state']
        score = number(row['structural_score'])
        return (state_order.get(label, 99), -(score if direction != 'short' else 100-score) if score is not None else D(101), key)
    order = sorted(themes, key=theme_key)
    theme_rank = {key: i for i, key in enumerate(order)}
    eligibility = {ticker: liquidity(bars, ticker, sessions, result['session'], rules)
                   for ticker in sorted({r['ticker'] for r in relationships})}
    rows, qualified = [], []
    for row in relationships:
        row['eligibility'] = eligibility[row['ticker']]
        theme = output[row['theme_id']]
        row['qualifies'] = bool(theme['researchable'] and row['role'] in ('Core', 'Enabler') and row['eligibility']['eligible'])
        w = number(field(row.get('relative', {}), 'w'))
        if row['qualifies']:
            rows.append(dict(ticker=row['ticker'], theme_id=row['theme_id'], role=row['role'], w=w,
                             theme_state=theme['state'] if direction == 'long' else theme['short_state'],
                             theme_rank=theme_rank[row['theme_id']], eligible=True, eligibility_reasons=[]))
            qualified.append(Qualification(row['ticker'], row['theme_id'], row['role'], w))
    rows.sort(key=lambda r: (r['theme_rank'], r['w'] is None,
                            -r['w'] if direction == 'long' and r['w'] is not None else r['w'] or D(0), r['ticker']))
    result['exports'] = exports(qualified, direction, mapping, theme_order=order)
    for row in relationships:
        assignment = result['exports']['assignments'].get(row['ticker'], {})
        row['assigned_section'] = assignment.get('assigned_section')
        row['also_qualifies_in'] = assignment.get('also_qualifies_in', [])
    # Retain historical context helpers, but never publish the removed research lens.
    if 'research' in result:
        result['research'].pop('countertrend', None)
        result['research']['focus'] = dict(label='Chart review' if direction else 'Observe', preferred_mode='directional')
    prior_direction = (previous_day or {}).get('market_direction') or (previous_day or {}).get('market', {}).get('decision', {}).get('direction')
    result['research_v2'] = dict(schema='themescope-research-v2', policy_version=rules['version'],
        themes=output, theme_order=order, liquidity=rules,
        list=dict(side=direction, rows=rows, stock_count=len({r['ticker'] for r in rows}), relationship_count=len(rows)),
        changes=dict(market_direction=result.get('market_direction'), previous_market_direction=prior_direction,
                     changed=prior_direction != result.get('market_direction') if prior_direction else None))
    return result
