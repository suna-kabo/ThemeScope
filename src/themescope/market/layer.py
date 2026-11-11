"""Separate roster breadth; unchanged Market Matrix function is the sole decision."""
from decimal import Decimal as D
from ..themes.calculations import calendar,usable,deterministic
from ..themes.index import ema,trend
from ..research_policy import market_rule,breadth_consensus
from .rosters import effective,warnings


def observation(symbol,bars,sessions):
    rows=[bars.get((symbol,s)) for s in sessions]
    prices=[r.adjusted_close if usable(r) else None for r in rows]
    a,b=(ema(prices,n) for n in (21,50))
    return {'close':prices[-1],'ema21':a,'ema50':b,'price_state':trend(prices[-1],a,b)}

@deterministic
def index_breadth(roster,bars,sessions):
    names=roster.tickers if roster else ()
    valid=[]
    for symbol in names:
        row=observation(symbol,bars,sessions)
        if row['price_state']!='Unavailable':valid.append(row)
    coverage=D(len(valid))/len(names) if names else D(0)
    a=b=None;state='Unavailable'
    if valid and coverage>=D('.8'):
        a=D(sum(r['close']>r['ema21'] for r in valid))/len(valid)*100
        b=D(sum(r['close']>r['ema50'] for r in valid))/len(valid)*100
        state='Positive' if a>=50 and b>=50 else 'Negative' if a<50 and b<50 else 'Mixed'
    return {'above_ema21':a,'above_ema50':b,'valid':len(valid),'configured':len(names),'coverage':coverage,'state':state}


def market_layer(bars,sessions,rosters):
    sessions=calendar(sessions);target=sessions[-1];contexts={}
    for symbol in ('SPY','QQQ','IWM'):
        row=observation(symbol,bars,sessions)
        if symbol!='IWM':
            roster=effective(rosters,symbol,target)
            row['breadth']=index_breadth(roster,bars,sessions)
            row['roster_warnings']=warnings(roster,target)
            row['roster_source']=roster.source if roster else None
            row['roster_effective_from']=roster.effective_from if roster else None
        contexts[symbol]=row
    consensus=breadth_consensus(contexts['SPY']['breadth']['state'],contexts['QQQ']['breadth']['state'])
    decision=market_rule(contexts['SPY']['price_state'],contexts['QQQ']['price_state'],consensus)
    return {'context':contexts,'breadth_consensus':consensus or 'Unavailable','decision':decision}
