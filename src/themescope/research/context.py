"""Additive completed-session research context. Never changes core qualification.

Legacy scores/W/trend, directional exports, membership and official history are
inputs only. New state lives under its own versioned snapshot contract.
"""
from decimal import Decimal as D
from pathlib import Path
from hashlib import sha256
import json
from ..themes.calculations import POLICY, number, usable, deterministic
from ..themes.history import ThemeHistory, compatible
from .primary import side

CONTRACT='themescope-research-1'
RULES=json.loads((Path(__file__).resolve().parents[3]/'config/vnext/research_context.json').read_text(encoding='utf-8'))


def field(row,key,default=None):
    return row.get(key,default) if isinstance(row,dict) else getattr(row,key,default)


@deterministic
def wilder_atr(bars,symbol,sessions,period=None):
    period=period or RULES['atr_period']
    if len(sessions)<period+1:return None
    previous=bars.get((symbol,sessions[0]))
    if not usable(previous):return None
    previous=number(previous.adjusted_close)
    ranges=[]
    for day in sessions[1:]:
        row=bars.get((symbol,day))
        if not usable(row):return None
        high,low,close=(number(getattr(row,k,None)) for k in ('adjusted_high','adjusted_low','adjusted_close'))
        if any(v is None or v<=0 for v in (high,low,close,previous)) or not low<=close<=high:return None
        ranges.append(max(high-low,abs(high-previous),abs(low-previous)))
        previous=close
    result=sum(ranges[:period])/period
    for value in ranges[period:]:result=((period-1)*result+value)/period
    return result if result>0 else None


@deterministic
def extension_state(distance):
    distance=number(distance)
    if distance is None:return {'state':'Unavailable','side':None,'magnitude':None}
    magnitude=abs(distance)
    direction='Upside' if distance>0 else 'Downside' if distance<0 else None
    label='Extended' if magnitude>=D(RULES['extended_at']) else 'Stretched' if magnitude>=D(RULES['stretched_at']) else 'Normal'
    return {'state':label if label=='Normal' else direction+' '+label,
            'side':direction,'magnitude':label}


def aggregate_extension(spy,qqq):
    a,b=extension_state(spy),extension_state(qqq)
    if 'Unavailable' in (a['state'],b['state']):return 'Unavailable'
    if a['side']==b['side'] and a['side'] and all(x['magnitude'] in ('Stretched','Extended') for x in (a,b)):
        return a['side']+(' Extended' if a['magnitude']==b['magnitude']=='Extended' else ' Stretched')
    return 'Normal'


@deterministic
def market_extension(market,bars,sessions):
    indices={}
    for ticker in ('SPY','QQQ'):
        atr=wilder_atr(bars,ticker,sessions)
        row=market.get('context',{}).get(ticker,{})
        close,average=number(row.get('close')),number(row.get('ema21'))
        distance=(close-average)/atr if atr and close is not None and average is not None else None
        indices[ticker]={'atr20':atr,'distance':distance,**extension_state(distance)}
    return {'state':aggregate_extension(indices['SPY']['distance'],indices['QQQ']['distance']),
            'indices':indices,'history_start':sessions[0] if sessions else None,'atr_period':RULES['atr_period']}


def research_focus(direction,extension):
    bias=side(direction)
    caution='Downside' if bias=='short' else 'Upside' if bias=='long' else None
    label='Directional' if bias else 'Observe'
    if caution and extension==caution+' Stretched':
        label='Directional + Countertrend Watch' if bias=='short' else 'Directional + Pullback-Risk Watch'
    elif caution and extension==caution+' Extended':
        label='Countertrend Highlighted' if bias=='short' else 'Pullback-Risk Highlighted'
    return {'label':label,'preferred_mode':'countertrend' if 'Highlighted' in label else 'directional'}


def relation(close,average):
    close,average=number(close),number(average)
    if close is None or average is None or close<=0 or average<=0:return 'Unavailable'
    return 'Above' if close>average else 'Below' if close<average else 'At'


def earned(themes):
    return any(field(t.get('history',{}),'signal_eligible',False) and not field(t.get('history',{}),'bootstrap',True) for t in themes)


def previous_compatible(snapshot,previous,sessions):
    return bool(previous and len(sessions)>1 and previous.get('session')==sessions[-2]
        and snapshot.get('methodology')==previous.get('methodology') and snapshot.get('theme_layer',{}).get('state')=='live'
        and earned(snapshot.get('themes',())) and earned(previous.get('themes',())))


def ema_transitions(snapshot,previous,sessions):
    compatible_previous=previous_compatible(snapshot,previous,sessions)
    result={}
    for ticker in ('SPY','QQQ','IWM'):
        current=snapshot.get('market',{}).get('context',{}).get(ticker,{})
        prior=(previous or {}).get('market',{}).get('context',{}).get(ticker,{}) if compatible_previous else {}
        result[ticker]={}
        for key in ('ema21','ema50'):
            now=relation(current.get('close'),current.get(key));old=relation(prior.get('close'),prior.get(key))
            available=now!='Unavailable' and old!='Unavailable'
            changed=available and now!=old
            message=(('Crossed '+now.lower() if now!='At' else 'Reached')+' '+key.upper()+' on '+snapshot['session']) if changed else None
            result[ticker][key]={'relation':now,'previous_relation':old,'changed':changed if available else None,
                'message':message,'previous_session':previous['session'] if available else None}
    return result


@deterministic
def canonical_ranks(themes):
    values={t['theme_id']:number(t.get('score')) for t in themes if t.get('status')=='active'}
    valid={key:value for key,value in values.items() if value is not None and D(0)<=value<=D(100)}
    # Competition ranks: 1, 2, 2, 4. Lexical ID only stabilizes display among ties.
    return {key:1+sum(v>value for v in valid.values()) for key,value in sorted(valid.items(),key=lambda pair:(-pair[1],pair[0]))}


def rank_changes(snapshot,previous,sessions):
    themes=snapshot.get('themes',());prior=(previous or {}).get('themes',())
    ranks=canonical_ranks(themes);old=canonical_ranks(prior)
    universe=sorted(t['theme_id'] for t in themes if t.get('status')=='active')
    prior_universe=sorted(t['theme_id'] for t in prior if t.get('status')=='active')
    old_rows={t['theme_id']:t for t in prior};rows={}
    for theme in themes:
        key=theme['theme_id'];rank=ranks.get(key);old_rank=old.get(key);change=None
        reason='unavailable_score' if rank is None else 'no_compatible_previous_session'
        if theme.get('status')!='active':reason='untracked_concept'
        elif rank is not None and previous_compatible(snapshot,previous,sessions):
            if key not in prior_universe:reason='newly_active_theme'
            elif old_rank is None:reason='newly_available_score'
            elif universe!=prior_universe:reason='active_universe_changed'
            elif ranks.keys()!=old.keys():reason='ranked_universe_changed'
            else:
                try:allowed=compatible(ThemeHistory(**old_rows[key]['history']),ThemeHistory(**theme['history']),sessions)
                except (TypeError,KeyError,ValueError):allowed=False
                if allowed:change=old_rank-rank;reason='comparable'
        rows[key]={'rank':rank,'previous_rank':old_rank,'change':change,'reason':reason,
                   'previous_session':previous['session'] if previous else None}
    return {'method':RULES['rank_method'],'ranked_total':len(ranks),'active_universe':universe,'themes':rows}


@deterministic
def countertrend(snapshot):
    bias=side(snapshot.get('market_direction'))
    themes={t['theme_id']:t for t in snapshot.get('themes',())}
    buckets={'resilient':[],'snapback':[]};boundary=D(str(POLICY['score_boundary']))
    if bias:
        for row in snapshot.get('relationships',()):
            theme=themes.get(row['theme_id'],{});score=number(theme.get('score'));w=number(field(row.get('relative',{}),'w'))
            eligible=row.get('eligibility',{})
            if (theme.get('status')!='active' or score is None or not D(0)<=score<=D(100) or w is None or w==0
                    or row.get('role') not in ('Core','Enabler') or not field(eligible,'available',False) or not field(eligible,'eligible',False)):
                continue
            trend=theme.get('index',{}).get('trend')
            if not ((bias=='short' and score<boundary and trend in ('Bearish','Mixed')) or
                    (bias=='long' and score>=boundary and trend in ('Bullish','Mixed'))):continue
            buckets['resilient' if w>0 else 'snapback'].append((row,w,score))
    output={}
    for key,values in buckets.items():
        values.sort(key=lambda item:((-item[1],-item[2]) if key=='resilient' else (item[1],item[2]))+(item[0]['ticker'],item[0]['theme_id']))
        rows=[{'ticker':r['ticker'],'theme_id':r['theme_id']} for r,w,score in values]
        seen=set();stocks=[]
        for row in rows:
            if row['ticker'] not in seen:seen.add(row['ticker']);stocks.append(row)
        label=('Resilient' if key=='resilient' else 'Snapback') if bias=='short' else ('Strong Leaders / Pullback Watch' if key=='resilient' else 'Relative Weakness')
        output[key]={'label':label,'rows':rows,'stocks':stocks,'stock_count':len(stocks),'relationship_count':len(rows)}
    symbols={r['ticker'] for b in output.values() for r in b['rows']}
    return {'available':bool(bias),'side':bias,'buckets':output,'stock_count':len(symbols),
            'relationship_count':sum(b['relationship_count'] for b in output.values()),
            'ordering_note':'Ordering reflects relative strength or weakness, not reversal probability.'}


def enrich(snapshot,bars,sessions,previous=None,companies=None):
    """Attach new research fields; all existing snapshot fields remain identical."""
    context=market_extension(snapshot.get('market',{}),bars,sessions)
    result=dict(snapshot)
    result['research']={'schema':CONTRACT,'policy_version':RULES['version'],
        'policy_hash':sha256(json.dumps(RULES,sort_keys=True).encode()).hexdigest(),
        'extension':context,'focus':research_focus(snapshot.get('market_direction'),context['state']),
        'ema_transitions':ema_transitions(snapshot,previous,sessions),'ranks':rank_changes(snapshot,previous,sessions),
        'countertrend':countertrend(snapshot),'companies':dict(companies or {})}
    return result
