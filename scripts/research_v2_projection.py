"""Validate supplied presentation consistency, without fetching or calculating prices."""
from decimal import Decimal
import re
from datetime import date
from hashlib import sha256
import json
from src.themescope.research.state_rules import state


def metric(value):
    return None if value is None else Decimal(str(value))


def validate_v2(snapshot):
    research=snapshot['research_v2'];themes=research['themes'];order=research['theme_order']
    direction=snapshot['market_direction'].lower()
    side={'long bias':'long','selective long':'long','short bias':'short','selective short':'short',
          'neutral':None,'unclassified':None}.get(direction,'invalid')
    conviction='selective' if side and direction.startswith('selective') else 'full' if side else 'none'
    if (snapshot['market']['decision']['direction'].lower()!=direction or side=='invalid'
            or research['contract_revision']!=2 or research['current_side']!=side
            or research['list']['side']!=side or research['conviction']!=conviction):
        raise ValueError('Market-side contract mismatch')
    policy=research['policy']
    if research['policy_version']!=policy['version']:raise ValueError('Policy mismatch')
    allowed={'Leading','Improving','Fading','Lagging','Unavailable'}
    source_themes={t['theme_id']:t for t in snapshot['themes']}
    scores={key:metric(t['score']) for key,t in source_themes.items() if t['status']=='active' and t['score'] is not None}
    for key,row in themes.items():
        selected=row['long_state'] if side=='long' else row['short_state'] if side=='short' else None
        score=scores.get(key);rank=1+sum(value>score for value in scores.values()) if score is not None else None
        if (row['long_state'] not in allowed or row['short_state'] not in allowed
                or row['current_side']!=side or row['current_state']!=selected
                or metric(row['structural_score'])!=score or metric(row['strength_rank'])!=rank
                or metric(row['research_order_index'])!=order.index(key)
                or row['researchable']!=bool(side and source_themes[key]['status']=='active' and selected in ('Leading','Improving','Fading'))):
            raise ValueError('Theme semantics mismatch')
        recent=row['recent'];raw=metric(recent['raw_score_change'])
        if any(row[direction+'_state']!=state(score,raw,direction,policy) for direction in ('long','short')):
            raise ValueError('Side state disagrees with supplied strength/change')
        expected_delta=raw if side=='long' else -raw if side=='short' and raw is not None else None
        if metric(recent['directional_score_change'])!=expected_delta:
            raise ValueError('Directional change mismatch')
        if side is None and recent['directional_rank_change'] is not None:raise ValueError('Non-directional rank')
        if not recent['available'] and any(recent[field] is not None for field in
                ('raw_score_change','directional_score_change','raw_rank_change','directional_rank_change','breadth_change')):
            raise ValueError('Unavailable comparison carries changes')
    priorities={label:i for i,label in enumerate(policy['selective_state_order'] if conviction=='selective' else policy['state_order'])}
    def theme_key(key):
        if side is None:return (key,)
        score=metric(themes[key]['structural_score'])
        return (priorities.get(themes[key]['current_state'],99),
                (-score if side=='long' else score) if score is not None else Decimal(101),key)
    if order!=sorted(themes,key=theme_key):raise ValueError('Theme order mismatch')
    comparison=research['comparison']
    if (comparison['official_history'] is not False or comparison['current_session']!=snapshot['session']
            or comparison['basis_session']!=snapshot['session'] or comparison['basis']!='current_reviewed_membership'
            or comparison['methodology']!=snapshot['methodology']
            or metric(comparison['change_sessions'])!=metric(policy['change_sessions'])):
        raise ValueError('Comparison provenance mismatch')
    if comparison['available']:
        if (set(comparison['horizon_populations'])!={'21','63'} or not comparison['previous_session']
                or any(p['current']!=p['previous'] for p in comparison['horizon_populations'].values())
                or comparison['ranked_population']!=sorted(scores)
                or date.fromisoformat(comparison['previous_session'])>=date.fromisoformat(snapshot['session'])):
            raise ValueError('Incompatible percentile population')
        for i,horizon in enumerate(('21','63')):
            expected=sorted(k for k,t in source_themes.items() if t['status']=='active'
                            and t.get('returns') and t['returns'][i]['value'] is not None)
            if comparison['horizon_populations'][horizon]['current']!=expected:raise ValueError('Current population mismatch')
    if not re.fullmatch('[0-9a-f]{64}',comparison['membership_hash']):raise ValueError('Invalid comparison fingerprint')
    relationships={(r['ticker'],r['theme_id']):r for r in snapshot['relationships']}
    signatures={key:sha256(json.dumps(sorted((r['ticker'],r['role']) for r in relationships.values()
                    if r['theme_id']==key and r['role'] in ('Core','Enabler'))).encode()).hexdigest()
                for key,t in sorted(source_themes.items()) if t['status']=='active'}
    if comparison['membership_hash']!=sha256(json.dumps(signatures,sort_keys=True).encode()).hexdigest():
        raise ValueError('Membership fingerprint mismatch')
    for row in relationships.values():
        eligibility=row['eligibility'];close=metric(eligibility['close']);average=metric(eligibility.get('average_dollar_volume'))
        expected_eligible=bool(eligibility['available'] and close is not None and average is not None
            and close>metric(policy['price_floor_exclusive']) and average>=metric(policy['average_dollar_volume_floor']))
        if eligibility['eligible']!=expected_eligible:raise ValueError('Liquidity threshold mismatch')
        expected=bool(themes[row['theme_id']]['researchable'] and row['role'] in ('Core','Enabler') and row['eligibility']['eligible'])
        if row['qualifies']!=expected:raise ValueError('Qualification mismatch')
    rows=research['list']['rows']
    def row_key(row):
        w=metric(row['w'])
        return (metric(row['research_order_index']),w is None,(-w if side=='long' else w) if w is not None else Decimal(0),row['ticker'])
    if rows!=sorted(rows,key=row_key):raise ValueError('Stock order mismatch')
    for row in rows:
        source=relationships[row['ticker'],row['theme_id']];theme=themes[row['theme_id']]
        if (row['role']!=source['role'] or metric(row['w'])!=metric(source['relative']['w'])
                or row['theme_state']!=theme['current_state']
                or metric(row['research_order_index'])!=metric(theme['research_order_index'])
                or row['eligible'] is not True or row['eligibility_reasons']):
            raise ValueError('Research row mismatch')
    exported=snapshot['exports'];symbols={};by_theme={key:[r for r in rows if r['theme_id']==key] for key in order}
    for row in relationships.values():
        assignment=exported['assignments'].get(row['ticker'],{})
        if (row['assigned_section']!=assignment.get('assigned_section')
                or row['also_qualifies_in']!=assignment.get('also_qualifies_in',[])):
            raise ValueError('Relationship export placement mismatch')
    by_theme={key:value for key,value in by_theme.items() if value}
    if set(exported['individual'])!=set(by_theme):raise ValueError('Theme export set mismatch')
    for key,theme_rows in by_theme.items():
        lines=exported['individual'][key].splitlines()
        if len(lines)!=len(theme_rows):raise ValueError('Theme export count mismatch')
        for row,line in zip(theme_rows,lines):
            if row['ticker'] in symbols and symbols[row['ticker']]!=line:raise ValueError('Multi-theme symbol mismatch')
            symbols[row['ticker']]=line
    if len(set(symbols.values()))!=len(symbols) or set(exported['assignments'])!=set(symbols):
        raise ValueError('Combined symbol set mismatch')
    lines=[];seen=set()
    for key,theme_rows in by_theme.items():
        selected=[r for r in theme_rows if r['ticker'] not in seen]
        if selected:lines.append('###'+key)
        for row in selected:
            ticker=row['ticker'];seen.add(ticker);lines.append(symbols[ticker])
            others=sorted(r['theme_id'] for r in rows if r['ticker']==ticker and r['theme_id']!=key)
            if exported['assignments'][ticker]!={'assigned_section':key,'also_qualifies_in':others}:
                raise ValueError('Export assignment mismatch')
    if exported['combined']!='\n'.join(lines)+('\n' if lines else ''):raise ValueError('Combined order mismatch')
