"""Shared approved decision rules. No data access or execution advice."""
from __future__ import annotations
import math
from .metrics import observation_map, trend_metric, return_metric
from .ranking import average_ranks


def number(x):
    return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)


def price_state(close, ema21, ema50):
    if not all(number(x) and x > 0 for x in (close, ema21, ema50)):
        return None
    if close > ema21 and close > ema50:
        return 'Bullish'
    if close < ema21 and close < ema50:
        return 'Bearish'
    return 'Mixed'


def breadth_state(a, b, boundary=50):
    if not all(number(x) and 0 <= x <= 100 for x in (a, b)):
        return None
    return 'Positive' if a >= boundary and b >= boundary else 'Negative' if a < boundary and b < boundary else 'Mixed'


def market_direction(spy, qqq, breadth):
    if spy not in ('Bullish','Mixed','Bearish') or qqq not in ('Bullish','Mixed','Bearish'):
        return 'Unclassified'
    if spy == qqq == 'Bullish':
        return 'Long bias'
    if spy == qqq == 'Bearish':
        return 'Short bias'
    return {'Positive':'Selective long','Negative':'Selective short','Mixed':'Neutral'}.get(breadth,'Unclassified')


PRIORITIES = {
    'Long bias': ('Primary long research','Secondary long research','Low-priority long research','Low-priority long research'),
    'Selective long': ('Primary selective-long research','Secondary selective-long research','Low-priority long research','Low-priority long research'),
    'Neutral': ('Monitor',)*4,
    'Selective short': ('Low-priority weakness exception','Low-priority weakness exception','Primary short research','Secondary short research'),
    'Short bias': ('Low-priority weakness exception','Low-priority weakness exception','Secondary short research','Primary short research'),
    'Unclassified': ('No directional priority',)*4,
}
STATES = ('Leading','Improving','Fading','Lagging')


def priority(direction, state, close, ema50):
    if state not in STATES:
        return {'label':'No directional priority','group':3,'side':None,'reason':'ETF score inputs unavailable.'}
    label = PRIORITIES.get(direction, PRIORITIES['Unclassified'])[STATES.index(state)]
    side = 'long' if direction in ('Long bias','Selective long') else 'short' if direction in ('Short bias','Selective short') else None
    if side and (not number(close) or not number(ema50) or close <= 0 or ema50 <= 0 or (close <= ema50 if side == 'long' else close >= ema50)):
        return {'label':'Observation only','group':3,'side':side,'reason':f'{side.title()} research label requires anchor close strictly {"above" if side == "long" else "below"} EMA50.'}
    group = 0 if label.startswith('Primary') else 1 if label.startswith('Secondary') else 2
    return {'label':label,'group':group,'side':side,'reason':f'{direction}; {state}'+(f'; anchor {"above" if side == "long" else "below"} EMA50.' if side else '.')}


def priority_sort_key(row):
    p = row.get('research_priority', {})
    score = row.get('theme_score')
    return (p.get('group',3), (score if p.get('side') == 'short' else -score) if number(score) else math.inf, row['id'])


ACTION_SENTENCES = {
    'Long bias': 'Prioritise long-side theme research. Review actual setups separately.',
    'Selective long': 'Prioritise selective long-side theme research. Review actual setups separately.',
    'Neutral': 'Keep directional research balanced. Review actual setups separately.',
    'Selective short': 'Prioritise selective short-side theme research. Review actual setups separately.',
    'Short bias': 'Prioritise short-side theme research. Review actual setups separately.',
    'Unclassified': 'Required Market inputs are unavailable. No directional research priority is assigned.',
}


def canonical_decision(session, generated_hkt, contexts, themes, direction, combined):
    """Build the single deterministic presentation decision used by every page."""
    by_ticker = {row.get('ticker'): row for row in contexts}
    spy, qqq, iwm = (by_ticker.get(symbol, {}) for symbol in ('SPY', 'QQQ', 'IWM'))
    spy_price, qqq_price = spy.get('price_state'), qqq.get('price_state')
    unavailable = []
    for label, value in (('SPY Price State', spy_price), ('QQQ Price State', qqq_price)):
        if value is None:
            unavailable.append({'input': label, 'consequence': 'Market classification is Unclassified.'})
    if not (spy_price == qqq_price and spy_price in ('Bullish', 'Bearish')) and combined is None:
        unavailable.append({'input': 'Combined Breadth State', 'consequence': 'The selective Market matrix cell cannot be resolved.'})
    unanimous = spy_price == qqq_price and spy_price in ('Bullish', 'Bearish')
    if unavailable:
        explanation = ' '.join(f"{row['input']} is unavailable; {row['consequence']}" for row in unavailable)
        rule_id = 'required-input-unavailable'
    elif unanimous:
        explanation = (f'SPY and QQQ are both {spy_price}. Under the approved Market matrix, unanimous {spy_price} '
                       f'Price States produce {direction}. Combined Breadth is {combined}, which describes '
                       f'{"divided participation" if combined == "Mixed" else "participation context"} but does not reverse unanimous price direction.')
        rule_id = f'unanimous-{spy_price.lower()}'
    else:
        explanation = (f'SPY and QQQ do not have a unanimous Price State. Combined Breadth is {combined}. '
                       f'The approved Market matrix produces {direction}.')
        rule_id = f'selective-{str(combined).lower()}'
    groups = {'primary': [], 'secondary': [], 'exception': [], 'observation': []}
    for row in sorted(themes, key=priority_sort_key):
        label = row.get('research_priority', {}).get('label', 'No directional priority')
        key = 'primary' if label.startswith('Primary') else 'secondary' if label.startswith('Secondary') else 'exception' if label.startswith('Low-priority') else 'observation'
        row['research_priority']['category'] = key
        groups[key].append(row['id'])
    directional = direction in ('Long bias', 'Selective long', 'Short bias', 'Selective short')
    side = 'long' if direction in ('Long bias', 'Selective long') else 'short' if direction in ('Short bias', 'Selective short') else None
    defs = {}
    for key in groups:
        labels = sorted({next((t['research_priority']['label'] for t in themes if t['id'] == theme_id), '') for theme_id in groups[key]})
        states = [state for state, label in zip(STATES, PRIORITIES.get(direction, PRIORITIES['Unclassified'])) if ('primary' if label.startswith('Primary') else 'secondary' if label.startswith('Secondary') else 'exception' if label.startswith('Low-priority') else 'observation') == key] if key != 'observation' else [state for state in STATES if any(t['id'] in groups[key] and t.get('theme_state') == state for t in themes)]
        defs[key] = {'labels': labels, 'theme_states': states, 'ema50_guard': (f'Anchor close must be strictly {"above" if side == "long" else "below"} EMA50.' if directional and key != 'observation' else None)}
    guard_failures = [{'theme_id': row['id'], 'reason': row['research_priority'].get('reason')} for row in themes if row['research_priority'].get('label') == 'Observation only']
    if spy.get('breadth_state') and qqq.get('breadth_state') and spy.get('breadth_state') != qqq.get('breadth_state'):
        divergence = f"SPY Breadth is {spy['breadth_state']} while QQQ Breadth is {qqq['breadth_state']}. Participation is split across the two primary index universes. Price direction remains the Market-direction input under the approved matrix."
    elif unanimous and combined not in (None, 'Mixed') and ((spy_price == 'Bullish') != (combined == 'Positive')):
        divergence = f'Price direction is {spy_price} while Combined Breadth is {combined}. Price direction remains the Market-direction input under the approved matrix.'
    elif iwm.get('price_state') and unanimous and iwm['price_state'] != spy_price:
        divergence = f"SPY and QQQ are {spy_price} while IWM is {iwm['price_state']}. IWM and Russell 2000 Breadth are context only, with no vote or veto."
    elif combined is None:
        divergence = 'Combined Breadth is unavailable; alignment cannot be established.'
    else:
        divergence = 'Price direction and Breadth are aligned.'
    return {
        'session_date': session, 'generated_at_hkt': generated_hkt, 'market_classification': direction,
        'action_sentence': ACTION_SENTENCES[direction], 'matrix_rule_id': rule_id,
        'matrix_inputs': {'spy_price_state': spy_price, 'qqq_price_state': qqq_price, 'combined_breadth_state': combined},
        'reason': explanation, 'spy_price_state': spy_price, 'qqq_price_state': qqq_price,
        'iwm_price_state': iwm.get('price_state'), 'spy_breadth_state': spy.get('breadth_state'),
        'qqq_breadth_state': qqq.get('breadth_state'), 'combined_breadth_state': combined,
        'russell_2000_breadth_state': iwm.get('breadth_state'), 'priority_groups': groups,
        'priority_definitions': defs, 'guard_failures': guard_failures, 'divergence': divergence,
        'market_matrix': [{'spy':a, 'qqq':b, 'breadth':c, 'direction':market_direction(a,b,c)} for a in ('Bullish','Mixed','Bearish') for b in ('Bullish','Mixed','Bearish') for c in ('Positive','Mixed','Negative')],
        'priority_matrix': {market: dict(zip(STATES, labels)) for market, labels in PRIORITIES.items()},
        'unavailable_inputs': unavailable,
    }


def breadth(symbols, charts, calendar, session, settings, minimum=0):
    """Shared current denominator and paired t/t-5 denominator for both EMAs."""
    symbols = list(dict.fromkeys(symbols))
    prior = calendar[calendar.index(session)-5] if session in calendar and calendar.index(session) >= 5 else None
    def observations(day):
        valid = {}
        for symbol in symbols:
            chart = charts.get(symbol, {})
            close = observation_map(chart).get(day, {}).get('close')
            clean = {**chart, 'observations': [{**r, 'close':r.get('close') if number(r.get('close')) and r['close'] > 0 else None} for r in chart.get('observations',[])]}
            trend = trend_metric(clean, calendar, day, settings) if day else {}
            if all(number(x) and x > 0 for x in (close, trend.get('ema21'), trend.get('ema50'))):
                valid[symbol] = {str(n): close > trend[f'ema{n}'] for n in (21,50)}
        return valid
    current, earlier = observations(session), observations(prior)
    paired = set(current) & set(earlier)
    floor = settings.get('minimum_breadth_coverage', .8)
    def eligible(items):
        return bool(symbols) and len(items) >= minimum and len(items)/len(symbols) >= floor
    result = {}
    for n in ('21','50'):
        above = sum(v[n] for v in current.values())
        value = 100*above/len(current) if eligible(current) else None
        pair_now = 100*sum(current[s][n] for s in paired)/len(paired) if eligible(paired) else None
        pair_old = 100*sum(earlier[s][n] for s in paired)/len(paired) if eligible(paired) else None
        result[n] = {'value':value,'status':'valid' if value is not None else 'unavailable','above_count':above,'valid_count':len(current),'eligible_count':len(symbols),'configured_count':len(symbols),'coverage_pct':100*len(current)/len(symbols) if symbols else None,'reason':None if value is not None else 'Insufficient valid histories for both EMAs.','session_date':session,'prior_session':prior,'paired_valid_count':len(paired),'paired_current_pct':pair_now,'t_minus_5':pair_old,'change_5_pp':pair_now-pair_old if pair_now is not None else None,'change_method':'Same constituents at both dates'}
    return result


def score_values(values, minimum):
    valid = {k:v for k,v in values.items() if number(v)}
    if len(valid) < max(2, minimum):
        return {k:None for k in values}
    return {k:(100*(sum(v < x for x in valid.values()) + (sum(v == x for x in valid.values())-1)/2)/(len(valid)-1) if number(v) else None) for k,v in values.items()}


def apply(snapshot, raw):
    settings = snapshot['settings']
    weights = snapshot.get('score_methodology',{}).get('theme_score_weights',{})
    if weights != {'current_strength':.6,'medium_strength':.4}:
        raise ValueError('Approved score weights must be 0.60/0.40')
    charts = {**raw.get('charts',{}),**raw.get('v5',{}).get('charts',{}),**raw.get('v5',{}).get('iwm_breadth_charts',{})}
    calendar, session = raw['session_calendar'], snapshot['session_date']
    themes = snapshot['themes']
    minimum = max(2, math.ceil(settings.get('ranking_minimum_coverage',.8)*settings.get('configured_active_anchor_count',len(themes))))
    def cohort(day):
        rows = {}
        for theme in themes:
            returns = [return_metric(charts.get(theme['anchor'],{}),calendar,day,n).get('value') for n in (21,63)]
            if all(number(v) for v in returns): rows[theme['id']] = returns
        return rows
    current = cohort(session)
    p21 = score_values({t['id']:current.get(t['id'],[None,None])[0] for t in themes},minimum)
    p63 = score_values({t['id']:current.get(t['id'],[None,None])[1] for t in themes},minimum)
    snapshot['ranking_cohort'] = {'eligible':sorted(current),'excluded':[{ 'id':t['id'],'reason':'Both exact adjusted-return endpoints required.'} for t in themes if t['id'] not in current],'minimum_peers':minimum}
    for t in themes:
        a,b = p21[t['id']],p63[t['id']]
        t.update(current_strength_score=a,medium_strength_score=b,theme_score=.6*a+.4*b if a is not None else None,theme_state=STATES[(0 if a >= 50 else 2)+(0 if b >= 50 else 1)] if a is not None else None)
    ranks = average_ranks({t['id']:t['theme_score'] for t in themes})
    for t in themes:
        t['global_rank'] = t['rank_current'] = ranks[t['id']]
        # Until the exact same cohort has been established at both dates, omit comparison.
        t['rank_t_minus_5'] = t['rank_change_5'] = None
        t['rank_change_reason'] = 'Common historical comparison cohort not established.'
        symbols = [m['ticker'] for m in t.get('selected',[])]
        metrics = breadth(symbols,charts,calendar,session,settings,settings.get('minimum_breadth_sample',8))
        t['theme_watchlist_breadth'] = metrics
        for n,m in metrics.items():
            for suffix,key in (('pct','value'),('above','above_count'),('valid','valid_count'),('change_5_pp','change_5_pp')):
                t[f'theme_breadth{n}_{suffix}'] = m[key]
    states = {}
    for row in snapshot.get('context',[]):
        ticker = row['ticker']
        mapped = raw.get('v5',{}).get('mapped_universes',{}).get(ticker,{})
        roster = raw.get('v5',{}).get('index_universes',{}).get(ticker,{})
        if roster.get('members'):
            symbols = [m['symbol'] for m in roster['members']]
        elif roster.get('rows'):
            symbols = []
            for index, item in enumerate(roster['rows']):
                kind = str(item.get('security_type') or 'EQUITY').casefold()
                if kind != 'equity': continue
                symbol = item.get('ticker')
                symbols.append(str(symbol).replace('.','-') if symbol and symbol != '-' else f'unresolved-{index}')
        else:
            symbols = [s for c in mapped.get('companies',[]) for s in c.get('symbols',[])]
        metrics = breadth(symbols,charts,calendar,session,settings)
        row['index_breadth'] = metrics
        for n,m in metrics.items():
            row[f'breadth{n}_change_5_pp'] = m['change_5_pp']
            row[f'breadth{n}_t_minus_5'] = m['t_minus_5']
        states[ticker] = {'price':price_state(row.get('price_close'),row.get('ema21'),row.get('ema50')),'breadth':breadth_state(metrics['21']['value'],metrics['50']['value'])}
        row['price_state'] = states[ticker]['price']
        row['breadth_state'] = states[ticker]['breadth']
    a,b = states.get('SPY',{}),states.get('QQQ',{})
    combined = a.get('breadth') if a.get('breadth') == b.get('breadth') else 'Mixed'
    if not a.get('breadth') or not b.get('breadth'): combined = None
    direction = market_direction(a.get('price'),b.get('price'),combined)
    snapshot['market_classification'] = {'direction':direction,'combined_breadth':combined,'inputs':states,'reason':f'SPY {a.get("price") or "unavailable"}; QQQ {b.get("price") or "unavailable"}; breadth {combined or "unavailable"}.','breadth_note':None if combined else 'Selective tilt unavailable'}
    for t in themes:
        t['research_priority'] = priority(direction,t.get('theme_state'),t.get('price_close'),t.get('ema50'))
    snapshot['score_methodology'] = {'current_strength_weights':{'return21_percentile':1.0},'medium_strength_weights':{'return63_percentile':1.0},'theme_score_weights':weights,'state_threshold':50,'method':'Cross-sectional ETF momentum'}
    for t in themes:
        for key in ('current_strength_score','medium_strength_score','theme_score'):
            t.setdefault('field_status',{})[key] = {'value':t[key],'status':'valid' if t[key] is not None else 'unavailable','reason':None if t[key] is not None else 'Shared 21/63 ETF peer cohort below minimum.'}
        for n,m in t['theme_watchlist_breadth'].items():
            t[f'breadth_status_{n}'] = m['status']
            t[f'breadth_unavailable_reason_{n}'] = m['reason']
            t['field_status'][f'theme_breadth{n}_pct'] = m
    snapshot['historical_rank_method'] = 'Unavailable until a common comparison cohort is established.'
    return snapshot
