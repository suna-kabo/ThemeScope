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
from .state_rules import state

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


def state_reason(label, comparable, direction, score, market_direction):
    if direction is None:
        return ('Market direction is unclassified; no directional research selection'
                if str(market_direction).lower()=='unclassified' else
                'No directional market bias; Long and Short states are context only')
    reasons = {
        'long': {'Leading':'Higher structural strength supports Long research without material recent weakening',
                 'Fading':'Structurally strong, but raw theme strength weakened materially over five sessions',
                 'Improving':'Raw theme strength improved materially, but is below the Long structural boundary',
                 'Lagging':'Lower structural strength without material recent improvement for Long research'},
        'short': {'Leading':'Lower structural strength supports Short research without material recent recovery',
                  'Fading':'Structurally weak, but raw theme strength recovered materially, reducing Short-side relevance',
                  'Improving':'Raw theme strength weakened materially, improving Short-side relevance before structural weakness',
                  'Lagging':'Higher structural strength without material recent weakening for Short research'}}
    text = reasons[direction].get(label,'Structural strength is unavailable')
    if number(score)==50 and label in ('Leading','Fading'):
        text = 'At the structural midpoint, included for '+direction.title()+' research'
        if label=='Fading':text += '; recent change reduces relevance on this side'
    if not comparable and label in ('Leading','Lagging'):
        text = ('At the structural midpoint' if number(score)==50 else
                ('Higher' if number(score)>50 else 'Lower')+' structural strength')
        text += ' for '+direction.title()+' research; five-session comparison unavailable'
    return text


@deterministic
def recent_change(snapshot, previous, sessions, rules, provenance=None):
    """Compare cross-sectional scores, independently of refresh/accounting history."""
    direction=side(snapshot.get('market_direction'))
    provenance=dict(provenance or {})
    empty = dict(available=False, comparison_session=provenance.get('previous_session'),
                 raw_score_change=None, directional_score_change=None, raw_rank_change=None,
                 directional_rank_change=None, breadth_change=None,
                 reason=provenance.get('reason','no_compatible_prior_basis'))
    end = sessions.index(snapshot['session'])
    horizon = rules['change_sessions']
    if end < horizon:
        return {}, dict(empty,reason='insufficient_completed_history')
    if not previous or provenance.get('available') is not True or previous.get('session') != sessions[end-horizon]:
        return {}, empty
    current = {t['theme_id']: t for t in snapshot['themes'] if t['status'] == 'active'}
    old = {t['theme_id']: t for t in previous.get('themes', ()) if t['status'] == 'active'}
    if snapshot['methodology'] != previous.get('methodology') or current.keys() != old.keys():
        return {}, dict(empty, reason='methodology_or_membership_changed')
    signatures_match = all(t.get('research_member_signature') and t['research_member_signature'] == old[k].get('research_member_signature')
                           for k,t in current.items())
    if not signatures_match:
        return {}, dict(empty, reason='methodology_or_membership_changed')
    expected_hash=sha256(json.dumps({key:t['research_member_signature'] for key,t in sorted(current.items())},sort_keys=True).encode()).hexdigest()
    if (provenance.get('membership_hash')!=expected_hash or provenance.get('current_session')!=snapshot['session']
            or provenance.get('basis_session')!=snapshot['session'] or provenance.get('methodology')!=snapshot['methodology']
            or provenance.get('basis')!='current_reviewed_membership' or provenance.get('official_history') is not False):
        return {}, dict(empty,reason='no_compatible_prior_basis')
    ranks, prior_ranks = canonical_ranks(snapshot['themes']), canonical_ranks(previous['themes'])
    def horizon_population(rows, horizon):
        return {key for key,theme in rows.items() if len(theme.get('returns') or ())>horizon
                and number(field(theme['returns'][horizon], 'value')) is not None}
    if (ranks.keys() != prior_ranks.keys() or any(horizon_population(current, i) != horizon_population(old, i)
                                                for i in (0,1))):
        return {}, dict(empty, reason='ranked_universe_changed')
    def side_ranks(rows):
        if direction=='long':return canonical_ranks(tuple(rows.values()))
        if direction is None:return {}
        values={key:number(t.get('score')) for key,t in rows.items() if number(t.get('score')) is not None}
        return {key:1+sum(other<score for other in values.values()) for key,score in values.items()}
    current_side_ranks,old_side_ranks=side_ranks(current),side_ranks(old)
    result = {}
    for key, theme in current.items():
        before = old[key]
        score, prior = number(theme.get('score')), number(before.get('score'))
        if score is None or prior is None:
            result[key] = dict(empty, reason='unavailable_score')
            continue
        a = number(field(theme.get('breadth', [{}])[0], 'value'))
        b = number(field(before.get('breadth', [{}])[0], 'value'))
        delta=score-prior
        result[key] = dict(available=True, comparison_session=previous['session'], raw_score_change=delta,
                           directional_score_change=delta if direction=='long' else -delta if direction=='short' else None,
                           raw_rank_change=prior_ranks[key]-ranks[key],
                           directional_rank_change=old_side_ranks[key]-current_side_ranks[key] if direction else None,
                           breadth_change=a-b if a is not None and b is not None else None, reason='comparable')
    return result, empty


@deterministic
def attach(snapshot, bars, sessions, mapping, *, previous=None, comparison_provenance=None,
           previous_day=None, rules=None, related=()):
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
    if comparison_provenance is None:
        comparison_provenance=dict(version='themescope-same-basis-comparison-1',available=False,
            reason='no_compatible_prior_basis',basis='current_reviewed_membership',basis_session=result['session'],
            current_session=result['session'],previous_session=None,change_sessions=rules['change_sessions'],
            methodology=result['methodology'],membership_hash=sha256(json.dumps(
                {key:t['research_member_signature'] for key,t in sorted(themes.items()) if t['status']=='active'},sort_keys=True).encode()).hexdigest(),
            official_history=False,horizon_populations={},ranked_population=[])
    changes, unavailable = recent_change(result, previous, sessions, rules,comparison_provenance)
    comparison_provenance=dict(comparison_provenance)
    if comparison_provenance['available'] and not any(row['available'] for row in changes.values()):
        comparison_provenance.update(available=False,reason=unavailable['reason'])
    ranks = canonical_ranks(result['themes'])
    direction = side(result.get('market_direction'))
    conviction='selective' if direction and str(result.get('market_direction','')).lower().startswith('selective') else 'full' if direction else 'none'
    output = {}
    for key, theme in themes.items():
        change = changes.get(key, unavailable)
        score = theme.get('score') if theme['status'] == 'active' else None
        long_state = state(score, change['raw_score_change'], 'long', rules)
        short_state = state(score, change['raw_score_change'], 'short', rules)
        selected = long_state if direction == 'long' else short_state if direction == 'short' else None
        breadth = theme.get('breadth', ())
        sample = breadth[0] if breadth else {}
        percent, total = number(field(sample, 'value')), field(sample, 'valid', 0)
        above = (theme.get('breadth_above') or [None])[0]
        if above is None and percent is not None:
            above = (percent*D(str(total))/100).to_integral_value()
        if percent is None and above is not None and total:
            percent = D(above)/D(total)*100
        output[key] = dict(long_state=long_state, short_state=short_state, current_state=selected,
                           structural_score=score,recent=dict(change), strength_rank=ranks.get(key), current_side=direction,
                           researchable=selected in ('Leading', 'Improving', 'Fading'),
                           reason=state_reason(selected, change['available'],direction,score,result.get('market_direction')),
                           breadth=dict(above=above,
                                        total=total, percent=percent,
                                        small_sample=total < rules['breadth_small_sample']))
    state_order = {name: i for i, name in enumerate(rules['selective_state_order'] if conviction=='selective' else rules['state_order'])}
    def theme_key(key):
        row = output[key]
        if direction is None:return (key,)
        label = row['current_state']
        score = number(row['structural_score'])
        return (state_order.get(label, 99), -(score if direction=='long' else 100-score) if score is not None else D(101), key)
    order = sorted(themes, key=theme_key)
    theme_rank = {key: i for i, key in enumerate(order)}
    for key,row in output.items():row['research_order_index']=theme_rank[key]
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
                             theme_state=theme['current_state'],
                             research_order_index=theme_rank[row['theme_id']], eligible=True, eligibility_reasons=[]))
            qualified.append(Qualification(row['ticker'], row['theme_id'], row['role'], w))
    rows.sort(key=lambda r: (r['research_order_index'], r['w'] is None,
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
    result['today_plan']=('Reduced conviction: established structural themes precede early improvement. ' if conviction=='selective' else '')
    result['today_plan']+=(f'Review {direction.title()}-side themes and the Daily Research List.' if direction else
        'Market evidence is unavailable. No directional Daily Research List.' if str(result.get('market_direction','')).lower()=='unclassified' else
        'No directional Daily Research List. Review market and theme context.')
    prior_direction = (previous_day or {}).get('market_direction') or (previous_day or {}).get('market', {}).get('decision', {}).get('direction')
    result['research_v2'] = dict(schema='themescope-research-v2', contract_revision=2,policy_version=rules['version'],
        current_side=direction,conviction=conviction,themes=output,theme_order=order,policy=rules,
        comparison=dict(comparison_provenance or dict(available=False,reason=unavailable['reason'],official_history=False)),
        list=dict(side=direction, rows=rows, stock_count=len({r['ticker'] for r in rows}), relationship_count=len(rows)),
        changes=dict(market_direction=result.get('market_direction'), previous_market_direction=prior_direction,
                     changed=prior_direction != result.get('market_direction') if prior_direction else None))
    return result
