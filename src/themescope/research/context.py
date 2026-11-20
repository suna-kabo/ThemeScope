"""Additive completed-session research context. Never changes core qualification.

Legacy scores/W/trend, directional exports, membership and official history are
inputs only. New state lives under its own versioned snapshot contract.
"""
from decimal import Decimal as D
from pathlib import Path
from hashlib import sha256
import json
from ..themes.calculations import number, usable, deterministic

CONTRACT='themescope-research-1'


def load_rules(path):
    return json.loads(path.read_text(encoding='utf-8'))


RULES=load_rules(Path(__file__).resolve().parents[3]/'config/vnext/research_context.json')


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
def extension_state(distance, rules=RULES):
    distance=number(distance)
    if distance is None:return {'state':'Unavailable','side':None,'magnitude':None}
    magnitude=abs(distance)
    direction='Upside' if distance>0 else 'Downside' if distance<0 else None
    label='Extended' if magnitude>=D(rules['extended_at']) else 'Stretched' if magnitude>=D(rules['stretched_at']) else 'Normal'
    return {'state':label if label=='Normal' else direction+' '+label,
            'side':direction,'magnitude':label}


def aggregate_extension(spy,qqq,rules=RULES):
    a,b=extension_state(spy,rules),extension_state(qqq,rules)
    if 'Unavailable' in (a['state'],b['state']):return 'Unavailable'
    if a['side']==b['side'] and a['side'] and all(x['magnitude'] in ('Stretched','Extended') for x in (a,b)):
        return a['side']+(' Extended' if a['magnitude']==b['magnitude']=='Extended' else ' Stretched')
    return 'Normal'


@deterministic
def market_extension(market,bars,sessions,rules=RULES):
    indices={}
    for ticker in ('SPY','QQQ'):
        atr=wilder_atr(bars,ticker,sessions,rules['atr_period'])
        row=market.get('context',{}).get(ticker,{})
        close,average=number(row.get('close')),number(row.get('ema21'))
        distance=(close-average)/atr if atr and close is not None and average is not None else None
        indices[ticker]={'atr20':atr,'distance':distance,**extension_state(distance,rules)}
    return {'state':aggregate_extension(indices['SPY']['distance'],indices['QQQ']['distance'],rules),
            'indices':indices,'history_start':sessions[0] if sessions else None,'atr_period':rules['atr_period']}


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


def enrich(snapshot,bars,sessions,previous=None,companies=None,*,rules=RULES):
    """Attach new research fields; all existing snapshot fields remain identical."""
    context=market_extension(snapshot.get('market',{}),bars,sessions,rules)
    result=dict(snapshot)
    result['research']={'schema':CONTRACT,'policy_version':rules['version'],
        'policy_hash':sha256(json.dumps(rules,sort_keys=True).encode()).hexdigest(),
        'extension':context,'ema_transitions':ema_transitions(snapshot,previous,sessions),
        'companies':dict(companies or {})}
    return result
