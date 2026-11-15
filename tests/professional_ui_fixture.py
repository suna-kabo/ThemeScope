"""Consistent backend-generated research fixtures; all price paths are fictional."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal as D
import json

from vnext_prelaunch_fixture import PrelaunchFixture
from src.themescope.research.comparison import reconstruct
from src.themescope.research.context import enrich
from src.themescope.research.v2 import attach
from src.themescope.research.primary import priority
from src.themescope.research_policy import ACTION_SENTENCES, market_rule
from src.themescope.storage import canonical


def research_states(fixture, base, *, bars=None, sessions=None):
    """Supply six explicit Market Matrix cells; regenerate every v2 derived field.

    Market inputs are manufactured observations, independent of the stock-price
    paths. They are passed through the real Matrix rule, not inferred in the UI.
    Theme metrics and five-session comparisons come only from synthetic bars.
    """
    bars=bars or {(b.ticker,b.session):b for b in fixture.bars}
    sessions=sessions or fixture.sessions[:fixture.sessions.index(base['session'])+1]
    mapping={r['ticker']:{'status':'verified','symbol':'FIXTURE:'+r['ticker']} for r in base['relationships']}
    prior,provenance=reconstruct(fixture.config,bars,sessions,base['session'],current=base)
    cases=(('Bullish','Bullish','Positive'),('Bullish','Mixed','Positive'),
           ('Bullish','Bearish','Mixed'),('Bearish','Mixed','Negative'),
           ('Bearish','Bearish','Negative'),(None,'Bullish',None))
    result={}
    for spy,qqq,consensus in cases:
        data=deepcopy(base)
        decision=market_rule(spy,qqq,consensus)
        data['market_direction']=decision['direction']
        data['market']['decision']=decision
        for theme in data['themes']:
            label=priority(decision['direction'],theme['score'],theme['index']['trend'],theme['transition'])
            theme['priority']=label;theme['history']['priority']=label
        data['today_plan']=ACTION_SENTENCES[decision['direction']]
        data['market']['breadth_consensus']=consensus or 'Unavailable'
        for ticker,classification in (('SPY',spy),('QQQ',qqq)):
            row=data['market']['context'][ticker]
            close=D(row['close'])
            row['price_state']=classification or 'Unavailable'
            if classification=='Bullish':row.update(ema21=close-1,ema50=close-2)
            elif classification=='Bearish':row.update(ema21=close+1,ema50=close+2)
            elif classification=='Mixed':row.update(ema21=close-1,ema50=close+1)
            else:row.update(close=None,ema21=None,ema50=None)
            row['breadth'].update(state=consensus or 'Unavailable',
                above_ema21=75 if consensus=='Positive' else 25 if consensus=='Negative' else 75 if consensus=='Mixed' else None,
                above_ema50=75 if consensus=='Positive' else 25 if consensus in ('Negative','Mixed') else None)
        data=enrich(data,bars,sessions,companies=data.get('research',{}).get('companies',{}))
        data=attach(data,bars,sessions,mapping,previous=prior,comparison_provenance=provenance)
        result[decision['direction']]=json.loads(canonical(data))
    return result


def make(folder):
    fixture=PrelaunchFixture(folder,full=True);fixture.target='2026-11-10'
    end=fixture.sessions.index(fixture.target)
    affinity={}
    for index,theme in enumerate(sorted(fixture.config.themes,key=lambda t:t.theme_id)):
        for member in fixture.config.members_on(theme.theme_id,fixture.target):
            affinity.setdefault(member.ticker,index)
    bars=[]
    for bar in fixture.bars:
        ramp=D(max(0,min(5,fixture.sessions.index(bar.session)-(end-5))))/5
        shock=D('.01')*(-1 if affinity.get(bar.ticker,0)%4<2 else 1) if bar.ticker in affinity else D(0)
        factor=1+ramp*shock
        bars.append(replace(bar,close=bar.close*factor,adjusted_close=bar.adjusted_close*factor))
    fixture.bars=tuple(bars)
    base=fixture.service.refresh()
    assert base is not None,fixture.service.status()
    states=research_states(fixture,fixture.service.snapshot())
    return fixture,states['Long bias'],states['Short bias']
